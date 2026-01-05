# bot/bot_client.py
import discord
from discord.ext import commands


def create_bot() -> commands.Bot:
    intents = discord.Intents.all()
    return commands.Bot(command_prefix="?", intents=intents)
