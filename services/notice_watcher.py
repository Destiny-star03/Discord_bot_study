# services/notice_watcher.py
import asyncio
import json
import os
import discord
import io
import requests
from discord import AllowedMentions
from discord.ext import commands, tasks

from config import (
    SCHOOL_NOTICE_URL,
    SCHOOL_NOTICE_CHANNEL_ID,
    CHECK_INTERVAL_SECONDS,
    STATE_FILE,
    ROLE_ID_TEST,
)
from crawler.school_notice import fetch_school_notices
from crawler.school_notice_detail import fetch_notice_detail
from models.notice import Notice

allowed = AllowedMentions(roles=True)


def _load_last_id() -> str | None:
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("last_school_notice_id")
    except Exception:
        return None


def _save_last_id(last_id: str) -> None:
    data = {"last_school_notice_id": last_id}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _pick_new_notices(notices: list[Notice], last_id: str | None) -> list[Notice]:
    # notices는 최신순(0번이 최신)이라고 가정
    if last_id is None:
        # 최초 실행: 스팸 방지로 최신 1개만(원하면 []로 바꿔서 첫 실행에 알림 0개 가능)
        return notices[:1]

    new_items: list[Notice] = []
    for n in notices:
        if n.notice_id == last_id:
            break
        new_items.append(n)
    return new_items


def _trim(text: str, limit: int = 1500) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...(이하 생략)"


async def _download_bytes(url: str, referer: str | None = None) -> tuple[bytes, str]:
    def _get():
        headers = {"User-Agent": "Mozilla/5.0"}
        if referer:
            headers["Referer"] = referer
        r = requests.get(url, timeout=15, headers=headers)
        r.raise_for_status()
        return r.content, r.headers.get("Content-Type", "")

    return await asyncio.to_thread(_get)


class SchoolNoticeWatcher:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self.loop.start()

    @tasks.loop(seconds=CHECK_INTERVAL_SECONDS)
    async def loop(self):
        await self.bot.wait_until_ready()

        # 채널 가져오기(캐시에 없으면 fetch)
        channel = self.bot.get_channel(SCHOOL_NOTICE_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(SCHOOL_NOTICE_CHANNEL_ID)
            except Exception:
                return

        if not isinstance(channel, discord.abc.Messageable):
            return

        last_id = _load_last_id()

        try:
            notices = await asyncio.to_thread(
                fetch_school_notices, SCHOOL_NOTICE_URL, 6
            )
        except Exception:
            return

        if not notices:
            return

        new_notices = _pick_new_notices(notices, last_id)

        if not new_notices:
            return

        # 오래된 것부터 보내기
        for n in reversed(new_notices):

            try:
                detail = await asyncio.to_thread(fetch_notice_detail, n.url)
            except Exception:
                detail = {"text": "", "images": [], "files": []}

            body = _trim(detail.get("text", ""), 1500)
            images = detail.get("images", [])
            files = detail.get("files", [])

            msg = (
                f"\n\n\n"
                f"\n📢[ **{n.title}** ]\n"
                f"- 부서: {n.dept or '-'} / 날짜: {n.date or '-'} / 조회수: {n.views if n.views is not None else '-'}\n"
            )

            if body:
                msg += f"\n{body}"

            if files:
                msg += f"\n\n[ 첨부파일은 아래 링크에 들어가 확인해주세요 ]"

            # 이미지/첨부는 너무 많이 보내지 말고 첫 개만

            if images:
                img_url = images[0]
                try:
                    img_bytes, ctype = await _download_bytes(img_url, referer=n.url)

                    ext = "jpg"
                    if "png" in ctype:
                        ext = "png"
                    elif "gif" in ctype:
                        ext = "gif"
                    elif "webp" in ctype:
                        ext = "webp"

                    filename = f"notice.{ext}"
                    file = discord.File(fp=io.BytesIO(img_bytes), filename=filename)

                    # ✅ 이미지가 보이도록 embed에 attachment 연결
                    embed = discord.Embed()
                    embed.set_image(url=f"attachment://{filename}")

                    msg += f"\n\n🔗 공지 바로가기: \n{n.url}\n\n"
                    msg += f"\n<@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> "
                    msg += f"\n======================================="

                    await channel.send(content=msg, file=file, embed=embed)
                    # ✅ 기존 msg는 그대로 content로 보내고, 파일+embed를 같이 전송

                except Exception:
                    # 실패하면 링크라도 남김(이미지 못 받아오는 경우 대비)
                    msg += f"\n\n🔗 공지 바로가기: \n{n.url}\n\n"
                    msg += f"\n<@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> "
                    msg += f"\n======================================="
                    await channel.send(msg)

            else:
                msg += f"\n\n🔗 공지 바로가기: \n{n.url}\n\n"
                msg += f"\n<@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> "
                msg += f"\n======================================="
                await channel.send(msg)

        # 최신 공지 ID 저장
        _save_last_id(notices[0].notice_id)
