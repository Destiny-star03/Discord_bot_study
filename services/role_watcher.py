# services/role_watcher.py
from __future__ import annotations

import json
import os
import discord
from discord.ext import commands

from ui.grade_role_view import GradeRoleView
from ui.role_embed import build_role_embed

ROLE_STATE_FILE = "role_state.json"


def _load_role_state() -> dict:
    if not os.path.exists(ROLE_STATE_FILE):
        return {}
    try:
        with open(ROLE_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_role_state(state: dict) -> None:
    with open(ROLE_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


class RoleWatcher:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True

        # persistent view 등록
        self.bot.add_view(GradeRoleView())

        # 자동으로 1회 생성/갱신 (기본 채널에)
        self.bot.loop.create_task(self.ensure_message())

    async def ensure_message(
        self, channel: discord.abc.Messageable | None = None
    ) -> discord.Message | None:
        """
        - channel을 넘기면 해당 채널에 생성/갱신
        - 안 넘기면 저장된 채널에 생성/갱신, 없으면 None
        """
        await self.bot.wait_until_ready()

        state = _load_role_state()
        channel_id = state.get("channel_id")
        message_id = state.get("message_id")

        if channel is None and channel_id:
            ch = self.bot.get_channel(channel_id)
            if ch is None:
                try:
                    ch = await self.bot.fetch_channel(channel_id)
                except Exception:
                    return None
            channel = ch

        if channel is None or not isinstance(channel, discord.abc.Messageable):
            return None

        embed = build_role_embed()
        view = GradeRoleView()

        if message_id:
            try:
                msg = await channel.fetch_message(message_id)  # type: ignore[attr-defined]
                await msg.edit(embed=embed, view=view)
                return msg
            except Exception:
                pass

        msg = await channel.send(embed=embed, view=view)
        _save_role_state({"channel_id": channel.id, "message_id": msg.id})
        return msg


def create_role_watcher(bot: commands.Bot) -> RoleWatcher:
    return RoleWatcher(bot)
