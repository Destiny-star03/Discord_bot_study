# services/notice_watcher.py
import asyncio
import json
import os
import io
import requests
import discord
from discord import AllowedMentions
from discord.ext import commands, tasks

from config import (
    SCHOOL_NOTICE_URL,
    SCHOOL_NOTICE_CHANNEL_ID,
    DEPT_NOTICE_URL,
    DEPT_NOTICE_CHANNEL_ID,
    CHECK_INTERVAL_SECONDS,
    STATE_FILE,
    ROLE_ID_TEST,
)

from crawler.school_notice import fetch_school_notices
from crawler.dept_notice import fetch_dept_notices
from crawler.school_notice_detail import (
    fetch_notice_detail as fetch_school_notice_detail,
)
from crawler.dept_notice_detail import fetch_notice_detail as fetch_dept_notice_detail

from models.notice import Notice

allowed = AllowedMentions(roles=True)


# ─────────────────────────────────────────────────────────
# STATE (학교/학과 key를 같은 파일에 같이 저장)
# ─────────────────────────────────────────────────────────
def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _get_last_id(state_key: str) -> str | None:
    state = _load_state()
    return state.get(state_key)


def _set_last_id(state_key: str, last_id: str) -> None:
    state = _load_state()
    state[state_key] = last_id
    _save_state(state)


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────
def _pick_new_notices(notices: list[Notice], last_id: str | None) -> list[Notice]:
    # notices는 최신순(0번이 최신)이라고 가정
    if last_id is None:
        # 최초 실행: 스팸 방지로 최신 1개만
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


# ─────────────────────────────────────────────────────────
# 통합 Watcher
# ─────────────────────────────────────────────────────────
class NoticeWatcher:
    """
    같은 로직으로 '학교공지/학과공지' 둘 다 돌릴 수 있도록 설정값만 주입하는 Watcher
    """

    def __init__(
        self,
        bot: commands.Bot,
        *,
        list_url: str,
        channel_id: int,
        state_key: str,  # 예: "last_school_notice_id"
        fetch_list_func,
        fetch_detail_func,
        limit: int = 3,
        label: str = "공지",  # 출력 앞머리 라벨
    ):
        self.bot = bot
        self.list_url = list_url
        self.channel_id = channel_id
        self.state_key = state_key
        self.fetch_list_func = fetch_list_func
        self.fetch_detail_func = fetch_detail_func
        self.limit = limit
        self.label = label
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self.loop.start()

    @tasks.loop(seconds=CHECK_INTERVAL_SECONDS)
    async def loop(self):
        await self.bot.wait_until_ready()

        # 채널 가져오기
        channel = self.bot.get_channel(self.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.channel_id)
            except Exception:
                return
        if not isinstance(channel, discord.abc.Messageable):
            return

        last_id = _get_last_id(self.state_key)

        # 목록 가져오기(스레드)
        try:
            notices: list[Notice] = await asyncio.to_thread(
                self.fetch_list_func, self.list_url, self.limit
            )
        except Exception:
            return

        if not notices:
            return

        new_notices = _pick_new_notices(notices, last_id)
        if not new_notices:
            return

        # 오래된 것부터
        for n in reversed(new_notices):
            try:
                detail = await asyncio.to_thread(self.fetch_detail_func, n.url)
            except Exception:
                detail = {"text": "", "images": [], "files": []}

            body = _trim(detail.get("text", ""), 1500)
            images = detail.get("images", [])
            files = detail.get("files", [])

            msg = (
                f"\n📢 **새 {self.label}**\n"
                f"[ **{n.title}** ]\n"
                f"- 부서: {n.dept or '-'} / 날짜: {n.date or '-'} / 조회수: {n.views if n.views is not None else '-'}\n"
            )

            if body:
                msg += f"\n{body}"

            if files:
                msg += "\n\n[ 첨부파일은 아래 링크에서 확인해주세요 ]"

            msg += f"\n\n🔗 공지 바로가기:\n{n.url}\n"
            msg += f"\n<@&{ROLE_ID_TEST}>"
            msg += "\n======================================="

            # 이미지 있으면 첨부+embed, 없으면 텍스트
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

                    embed = discord.Embed()
                    embed.set_image(url=f"attachment://{filename}")

                    await channel.send(
                        content=msg,
                        file=file,
                        embed=embed,
                        allowed_mentions=allowed,
                    )
                except Exception:
                    # 이미지 실패 시 링크만
                    msg += f"\n(이미지 링크): {img_url}\n"
                    await channel.send(msg, allowed_mentions=allowed)
            else:
                await channel.send(msg, allowed_mentions=allowed)

        # 최신 공지 ID 저장(가장 최신 0번)
        _set_last_id(self.state_key, notices[0].notice_id)


# ─────────────────────────────────────────────────────────
# 생성 헬퍼(메인에서 간단히 사용)
# ─────────────────────────────────────────────────────────
def create_school_notice_watcher(bot: commands.Bot) -> NoticeWatcher:
    return NoticeWatcher(
        bot,
        list_url=SCHOOL_NOTICE_URL,
        channel_id=SCHOOL_NOTICE_CHANNEL_ID,
        state_key="last_school_notice_id",
        fetch_list_func=fetch_school_notices,
        fetch_detail_func=fetch_school_notice_detail,
        limit=3,
        label="학교 공지",
    )


def create_dept_notice_watcher(bot: commands.Bot) -> NoticeWatcher:
    return NoticeWatcher(
        bot,
        list_url=DEPT_NOTICE_URL,
        channel_id=DEPT_NOTICE_CHANNEL_ID,
        state_key="last_dept_notice_id",
        fetch_list_func=fetch_dept_notices,
        fetch_detail_func=fetch_dept_notice_detail,
        limit=3,
        label="학과 공지",
    )
