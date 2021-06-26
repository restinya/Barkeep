import discord
import asyncio
import requests
import re

from discord.utils import get        
from discord.ext import commands
from math import floor
from configs.settings import command_prefix
from utils import accessDB, point_buy, alpha_emojis, db, VerboseMDStringifier, traceBack, checkForChar



class Item(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    @commands.group(case_insensitive=True)
    @is_log_channel()
    async def item(self, ctx):	
        shopCog = self.bot.get_cog('Item')
        pass
        
    async def cog_command_error(self, ctx, error):
        msg = None

        if isinstance(error, commands.CommandNotFound):
            await ctx.channel.send(f'Sorry, the command **`{command_prefix}{ctx.invoked_with}`** requires an additional keyword to the command or is invalid, please try again!')
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'charName':
                msg = "You're missing your character name in the command.\n"
            if error.param.name == 'searchQuery':
                msg = "You're missing your item name in the command.\n"
            elif error.param.name == "buyItem":
                msg = "You're missing the item you want to buy/sell in the command.\n"
            elif error.param.name == "spellName":
                msg = "You're missing the spell you want in the command.\n"
        elif isinstance(error, commands.CheckFailure):
            msg = "This channel or user does not have permission for this command. "
        elif isinstance(error, commands.BadArgument):
            print(error)
            # convert string to int failed
            msg = "The amount you want to buy or sell must be a number.\n"
        # bot.py handles this, so we don't get traceback called.
        elif isinstance(error, commands.CommandOnCooldown):
            return
        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
             msg = "Your \" placement seems to be messed up.\n"
        if msg:
            if ctx.command.name == "buy":
                msg += f"Please follow this format:\n```yaml\n{command_prefix}item buy \"character name\" \"item\" #```\n"
            elif ctx.command.name == "sell":
                msg += f"Please follow this format:\n```yaml\n{command_prefix}item sell \"character name\" \"item\" #```\n"
            elif ctx.command.name == "learn":
                msg += f"Please follow this format:\n```yaml\n{command_prefix}item learn \"character name\" \"spell name\"```\n"

            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)
        else:
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)