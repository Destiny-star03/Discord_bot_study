# bot/commands.py
import asyncio
from discord.ext import commands

# 인사
# def setup_commands(bot: commands.Bot) -> None:
#     @bot.command(name="안녕" ,help="인사말", aliases=["인사","하이"])
#     async def hello(ctx):
#         await ctx.send("{}아, 안녕".format(ctx.author.mention))


def setup_command(bot: commands.Bot) -> None:
    @bot.command()
    async def 따라하기(ctx, *, text):
        await ctx.send(text)
        
        

