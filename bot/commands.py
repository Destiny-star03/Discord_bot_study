# bot/commands.py
import asyncio
from discord.ext import commands
from crawler.school_notice_detail import fetch_notice_detail

#인사
# def setup_commands(bot: commands.Bot) -> None:
#     @bot.command(name="안녕" ,help="인사말", aliases=["인사","하이"])
#     async def hello(ctx):
#         await ctx.send("{}아, 안녕".format(ctx.author.mention))

def setup_command(bot: commands.Bot) -> None:
    @bot.command()
    async def 복사하기(ctx,*,text):
        await ctx.send(text)

SCHOOL_BBS_ID = "BBSMSTR_000000000590"

def setup_commands(bot: commands.Bot) -> None:
    @bot.command(name="공지본문")
    async def notice_body(ctx, url: str):
       
        data = await asyncio.to_thread(fetch_notice_detail, url)

        text = data["text"]
        images = data["images"]

        # 디스코드 메시지 2000자 제한 -> 안전하게 자르기
        MAX = 1800
        if len(text) > MAX:
            text = text[:MAX] + "\n...(이하 생략)"

        msg = f"📄 **공지 본문**\n{url}\n\n{text}"
        if images:
            msg += f"\n\n🖼 이미지(첫 장): {images[0]}"

        await ctx.send(msg)