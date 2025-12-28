<<<<<<< HEAD
import discord, random
from discord.ext import commands

import json
with open("Token.json", "r") as flie:
	data = json.load(flie)


bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())
TOKEN = data['TOKEN']
=======

# main
from config import DISCORD_TOKEN
import discord
import truststore
>>>>>>> 9f5d19884c9f60b5c93451eb8ed20db2bb195bee
<<<<<<< HEADimport truststore



from bot.bot_clinet import create_bot
from bot.commands import setup_commands, setup_command
from bot.commands import setup_command
from services.notice_watcher import (
    create_school_notice_watcher,
    create_dept_notice_watcher,
)

truststore.inject_into_ssl()
from utils.http_client import init_http

bot = create_bot()
init_http()
school_watcher = create_school_notice_watcher(bot)
dept_watcher = create_dept_notice_watcher(bot)

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN이 설정되지 않았습니다. .env파일을 확인하세요.")

setup_command(bot)


# 로그인
@bot.event
async def on_ready():
    school_watcher.start()
    dept_watcher.start()
    print(f"{bot.user.name}이(가) 연결 되었습니다.")
    await bot.change_presence(
        status=discord.Status.online, activity=discord.Game("테스트")
    )


# 봇 작동
bot.run(DISCORD_TOKEN)
