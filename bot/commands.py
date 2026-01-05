# bot/commands.py
import discord
from discord.ext import commands

from services.role_watcher import create_role_watcher

# 인사
# def setup_commands(bot: commands.Bot) -> None:
#     @bot.command(name="안녕" ,help="인사말", aliases=["인사","하이"])
#     async def hello(ctx):
#         await ctx.send("{}아, 안녕".format(ctx.author.mention))


def setup_command(bot: commands.Bot) -> None:
    @bot.command()
    async def 따라하기(ctx, *, text):
        await ctx.send(text)


def setup_role_commands(bot: commands.Bot):
    role_watcher = create_role_watcher(bot)

    @bot.command(name="rolesetup", help="역할 선택 메시지 생성/갱신 (관리자 전용)")
    async def rolesetup(ctx: commands.Context):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("관리자만 사용할 수 있습니다.")
            return

        msg = await role_watcher.ensure_message(ctx.channel)

        if msg is None:
            await ctx.send(
                "채널에 메시지를 생성/갱신하지 못했습니다. 권한/채널 타입을 확인하세요."
            )
            return

        await ctx.send(
            f"완료! 역할 선택 메시지를 생성/갱신했습니다. (message_id={msg.id})"
        )
