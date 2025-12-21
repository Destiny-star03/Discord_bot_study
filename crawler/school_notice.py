import discord
import requests
from discord.ext import commands
from config import SCHOOL_NOTICE_URL
from bs4 import BeautifulSoup

bot = commands.Bot(command_prefix="?", intents=discord.Intents.all())
baseUrl = SCHOOL_NOTICE_URL

