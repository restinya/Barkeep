import discord
import asyncio
import requests
import re

from discord.utils import get        
from discord.ext import commands
from math import floor
from configs.settings import command_prefix
from utils import accessDB, point_buy, alpha_emojis, db, VerboseMDStringifier, traceBack, checkForChar



class Reward(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    @commands.group(aliases=['r'], case_insensitive=True)
    async def reward(self, ctx):	
        pass
        
    async def cog_command_error(self, ctx, error):
        msg = None

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @commands.has_role('DM')
    @commands.command()
    async def encounter(self, ctx, user_list, level: int, renown: int):
        channel = ctx.channel
        author = ctx.author
        user = author.display_name
        user_name = author.name
        player_roster = [author] + ctx.message.mentions
        reward_format =  f'Please follow this format:\n```yaml\n{command_prefix}reward encounter "@player1 @player2 [...]" ENCOUNTERLVL RENOWN```'

        if '"' not in ctx.message.content:
            await channel.send(f"Make sure you put quotes **`\"`** around your list of players and retry the command!\n\n{reward_format}")
            self.timer.get_command('prep').reset_cooldown(ctx)
            return

        if author in ctx.message.mentions:
            #inform the user of the proper command syntax
            await channel.send(f"You cannot reward players with yourself in the player list! {reward_format}")
            self.timer.get_command('prep').reset_cooldown(ctx)
            return 

        reward_embed = discord.Embed()

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @commands.has_role('DM')
    @commands.command()
    async def levelup(self, ctx, user, char):
        channel = ctx.channel
        author = ctx.author
        user = author.display_name
        user_name = author.name