# bot/bot_client.py
import discord
from discord.ext import commands
from config import COMMAND_PREFIX

def create_bot() -> commands.Bot:
    intents = discord.Intents.all()
    return commands.Bot( command_prefix="?",intents=intents )