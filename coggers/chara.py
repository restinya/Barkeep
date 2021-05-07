import discord

from discord.ext import commands

class Character(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    async def cog_command_error(self, ctx, error):
        msg = None
        
        if isinstance(error, commands.BadArgument):
            # convert string to int failed
            msg = "Your stats and level need to be numbers. "

        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
             return
        elif isinstance(error, commands.CheckFailure):
            msg = "This channel or user does not have permission for this command. "
        elif isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'char':
                msg = ":warning: You're missing the character name in the command.\n"
            elif error.param.name == 'new_race':
                msg = ":warning: You're missing the new race in the command.\n"
            elif error.param.name == "name":
                msg = ":warning: You're missing the name for the character you want to create or respec.\n"
            elif error.param.name == "level":
                msg = ":warning: You're missing a level for the character you want to create.\n"
            elif error.param.name == "race":
                msg = ":warning: You're missing a race for the character you want to create.\n"
            elif error.param.name == "cclass":
                msg = ":warning: You're missing a class for the character you want to create.\n"
            elif error.param.name == 'bg':
                msg = ":warning: You're missing a background for the character you want to create.\n"
            elif error.param.name == 'sStr' or  error.param.name == 'sDex' or error.param.name == 'sCon' or error.param.name == 'sInt' or error.param.name == 'sWis' or error.param.name == 'sCha':
                msg = ":warning: You're missing a stat (STR, DEX, CON, INT, WIS, or CHA) for the character you want to create.\n"

            msg += "**Note: if this error seems incorrect, something else may be incorrect.**\n\n"


    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @commands.command()
    async def create(self, ctx, name, level: int, race, cclass, bg, sStr: int, sDex: int, sCon: int, sInt: int, sWis: int, sCha: int, magicItem, userID):
        name = name.strip()
        characterCog = self.bot.get_cog('Character')
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed()
        charEmbed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        charEmbed.set_footer(text="React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")
        charEmbedmsg = None
        abiNames = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

        charDict = {
          'User ID': str(author.id),
          'Name': name,
          'Level': int(level),
          'HP': 0,
          'Class': cclass,
          'Background': bg,
          'STR': int(sStr),
          'DEX': int(sDex),
          'CON': int(sCon),
          'INT': int(sInt),
          'WIS': int(sWis),
          'CHA': int(sCha),
          'Alignment': 'Unknown',
          'Reputation' : 0,
          'Renown': 0,
          'Magic Items': 'None',
          'Consumables': 'None',
          'Feats': 'None',
          'Inventory': {},
        }

        if not name:
            await channel.send(content=":warning: The name of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return

        if not level:
            await channel.send(content=":warning: The level of your character cannot be blank! Please try again.\n")

            self.bot.get_command('create').reset_cooldown(ctx)
            return

        if not race:
            await channel.send(content=":warning: The race of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return

        if not cclass:
            await channel.send(content=":warning: The class of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return
        
        if not bg:
            await channel.send(content=":warning: The background of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return

        # Name should be less then 65 chars
        if len(name) > 64:
            msg += ":warning: Your character's name is too long! The limit is 64 characters.\n"

        # Reserved for regex, lets not use these for character names please
        invalidChars = ["[", "]", "?", '"', "\\", "*", "$", "{", "+", "}", "^", ">", "<", "|"]

        for i in invalidChars:
            if i in name:
                msg += f":warning: Your character's name cannot contain `{i}`. Please revise your character name.\n"

        if msg == "":
            rRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'races',race)
            if charEmbedmsg == "Fail":
                return
            if not rRecord:
                msg += f'• {race} isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
            else:
                charDict['Race'] = rRecord['Name']

def setup(bot):
    bot.add_cog(Character(bot))