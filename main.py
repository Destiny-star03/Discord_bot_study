
# main
from config import DISCORD_TOKEN
import discord
import truststore

from bot.bot_clinet import create_bot
from bot.commands import setup_command, setup_role_commands
from services.notice_watcher import (
    create_school_notice_watcher,
    create_dept_notice_watcher,
)

from services.role_watcher import create_role_watcher
from utils.http_client import init_http

bot = create_bot()
init_http()

school_watcher = create_school_notice_watcher(bot)
dept_watcher = create_dept_notice_watcher(bot)
role_watcher = create_role_watcher(bot)

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN이 설정되지 않았습니다. .env파일을 확인하세요.")

setup_command(bot)
setup_role_commands(bot)


# 로그인
@bot.event
async def on_ready():
    role_watcher.start()

    school_watcher.start()
    dept_watcher.start()
    print(f"{bot.user.name}이(가) 연결 되었습니다.")
    await bot.change_presence(
        status=discord.Status.online, activity=discord.Game("만드는 중")
    )


# 봇 작동
bot.run(DISCORD_TOKEN)
