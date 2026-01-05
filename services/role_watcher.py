# services/role_watcher.py
from __future__ import annotations

import discord
from discord.ext import commands

from config import TEST_CHANNEL_ID2
from services.role_message_store import load_role_message_id, save_role_message_id
from ui.grade_role_view import GradeRoleView
from ui.role_embed import build_role_embed


class RoleWatcher:
    def __init__(
        self,
        bot: commands.Bot,
        *,
        channel_id: int,
        state_key: str = "role_message_id",
    ):
        self.bot = bot
        self.channel_id = channel_id
        self.state_key = state_key
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True

        # persistent view 등록
        self.bot.add_view(GradeRoleView())

        # 자동으로 1회 생성/갱신
        self.bot.loop.create_task(self.ensure_message())

    async def ensure_message(
        self, channel: discord.abc.Messageable | None = None
    ) -> discord.Message | None:
        """
        - channel을 넘기면 해당 채널에 생성/갱신
        - 안 넘기면 config의 ROLE_CHANNEL_ID 채널에 생성/갱신
        """
        await self.bot.wait_until_ready()

        if channel is None:
            ch = self.bot.get_channel(self.channel_id)
            if ch is None:
                try:
                    ch = await self.bot.fetch_channel(self.channel_id)
                except Exception:
                    return None
            channel = ch

        if not isinstance(channel, discord.abc.Messageable):
            return None

        embed = build_role_embed()
        view = GradeRoleView()

        msg_id = load_role_message_id(self.state_key)
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)  # type: ignore[attr-defined]
                await msg.edit(embed=embed, view=view)
                return msg
            except Exception:
                pass

        msg = await channel.send(embed=embed, view=view)
        save_role_message_id(self.state_key, msg.id)
        return msg


def create_role_watcher(bot: commands.Bot) -> RoleWatcher:
    return RoleWatcher(bot, channel_id=TEST_CHANNEL_ID2)
