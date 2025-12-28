# services/notice_watcher.py
import asyncio
import json
import os
import io
import discord
from discord import AllowedMentions
from discord.ext import commands, tasks
from utils.http_client import get as http_get

from config import (
    SCHOOL_NOTICE_URL,
    SCHOOL_NOTICE_CHANNEL_ID,
    DEPT_NOTICE_URL,
    DEPT_NOTICE_CHANNEL_ID,
    CHECK_INTERVAL_SECONDS,
    STATE_FILE,
    ROLE_ID_TEST,
    ROLE_ID_1,
    ROLE_ID_2,
    ROLE_ID_3,
    ROLE_ID_4,
)

# from crawler.school_notice import fetch_school_notices
# from crawler.dept_notice import fetch_dept_notices
from crawler.notices import fetch_school_notices, fetch_dept_notices
from crawler.notice_detail import (
    fetch_notice_detail as fetch_school_notice_detail,
    fetch_notice_detail as fetch_dept_notice_detail,
)
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
        r = http_get(url, timeout=15, referer=referer)
        r.raise_for_status()
        return r.content, r.headers.get("Content-Type", "")

    return await asyncio.to_thread(_get)


def _looks_like_broken_table_text(t: str) -> bool:
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if len(lines) < 40:
        return False
    short_ratio = sum(1 for ln in lines if len(ln) <= 2) / len(lines)
    # "수", "시", "호" 같은 단문 라인이 비정상적으로 많으면 표/전단지 텍스트일 확률이 큼
    if short_ratio >= 0.30:
        return True
    # 줄이 너무 많아도 위험 신호
    if len(lines) >= 120:
        return True
    return False


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
        limit: int = 10,
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

            body_raw = detail.get("text", "") or ""
            image_urls = detail.get("images", []) or []
            image_blobs = detail.get("image_blobs", []) or []
            files = detail.get("files", []) or []

            msg = (
                f"\n📢 **새 {self.label}**\n"
                f"[ **{n.title}** ]\n"
                f"- 부서: {n.dept or '-'} / 날짜: {n.date or '-'} / 조회수: {n.views if n.views is not None else '-'}\n"
            )
            has_any_image = bool(image_urls) or bool(image_blobs)

            # ✅ 전단지/표로 인해 텍스트가 깨져보이면(그리고 이미지가 있으면) 본문 생략
            if has_any_image and _looks_like_broken_table_text(body_raw):
                msg += "\n📌 본문이 표/전단지 형식이라 이미지와 링크로 안내합니다."
            else:
                body = _trim(body_raw, 1500)
                if body:
                    msg += f"\n{body}"

            if files:
                msg += "\n\n📎 첨부파일이 있습니다. (공지 링크에서 확인)"

            msg += f"\n\n🔗 공지 바로가기:\n{n.url}\n"
            msg += f"\n<@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}> <@&{ROLE_ID_TEST}>"
            msg += "\n======================================="

            # 이미지 있으면 첨부+embed, 없으면 텍스트
            if has_any_image:
                files_to_send: list[discord.File] = []
                embeds_to_send: list[discord.Embed] = []

                idx = 1

                for blob in image_blobs:
                    if idx > 2:
                        break
                    try:
                        ext = (blob.get("ext") or "jpg").lower()
                        raw = blob.get("bytes")
                        if not raw:
                            continue

                        filename = f"notice_{idx}.{ext}"
                        files_to_send.append(
                            discord.File(fp=io.BytesIO(raw), filename=filename)
                        )

                        embed = discord.Embed()
                        embed.set_image(url=f"attachment://{filename}")
                        embeds_to_send.append(embed)

                        idx += 1
                    except Exception:
                        continue

                for url in image_urls:
                    if idx > 2:
                        break
                    try:
                        img_bytes, ctype = await _download_bytes(url, referer=n.url)

                        ext = "jpg"
                        c = (ctype or "").lower()
                        if "png" in c:
                            ext = "png"
                        elif "gif" in c:
                            ext = "gif"
                        elif "webp" in c:
                            ext = "webp"

                        filename = f"notice_{idx}.{ext}"
                        files_to_send.append(
                            discord.File(fp=io.BytesIO(img_bytes), filename=filename)
                        )

                        embed = discord.Embed()
                        embed.set_image(url=f"attachment://{filename}")
                        embeds_to_send.append(embed)

                        idx += 1
                    except Exception:
                        continue

                if files_to_send:
                    await channel.send(
                        content=msg,
                        files=files_to_send,
                        embeds=embeds_to_send,
                        allowed_mentions=allowed,
                    )
                else:
                    # 이미지 전부 실패하면 텍스트만
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
        limit=1,
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
        limit=1,
        label="학과 공지",
    )
