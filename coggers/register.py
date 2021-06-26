import discord
import asyncio
import requests
import re

from discord.utils import get        
from discord.ext import commands
from math import floor
from configs.settings import command_prefix
from utils import accessDB, point_buy, alpha_emojis, db, VerboseMDStringifier, traceBack, checkForChar



class Register(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    @commands.group(aliases=['r'], case_insensitive=True)
    async def reward(self, ctx):	
        pass