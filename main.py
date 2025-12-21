from config import DISCORD_TOKEN
import discord
from bot.bot_clinet import create_bot
from bot.commands import setup_commands,setup_command


bot = create_bot()
setup_commands(bot)
setup_command(bot)

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN이 설정되지 않았습니다. .env파일을 확인하세요.")

#로그인
@bot.event
async def on_ready():
    print(f"{bot.user.name}이(가) 연결 되었습니다.")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game('테스트'))

#봇 작동
bot.run(DISCORD_TOKEN)