import discord
import os
import traceback

from discord.ext import commands
from discord.ext.commands import CommandNotFound, MissingPermissions

# Bot permissions invite link
#https://discord.com/api/oauth2/authorize?client_id=840056810488201276&permissions=808840256&scope=bot
# ------- COGS -------

COGS = [
    'coggers.chara'
]


class Barkeep(commands.Bot):
    def __init__(self, prefix, description=None, **options):
        super(Barkeep, self).__init__(prefix, help_command=None, description=description, **options)
        self.state = "init"

intents = discord.Intents(
    guilds=True, members=True, messages=True, reactions=True
)

bot = Barkeep(prefix='!', description=None, pm_help=True, activity = discord.Activity(name='Searching for more adventurers...', type=discord.ActivityType.playing), allowed_mentions=discord.AllowedMentions.none(), intents=intents)

@bot.event
async def on_ready():
    print(f'Logging in as {bot.user.name} {bot.user.id}\n')

@bot.event
async def on_resumed():
    print('Resumed.')

@bot.event
async def on_command_error(ctx, error):
    msg = None
    print(ctx.invoked_with)
    print(error)

    if isinstance(error, commands.CommandNotFound):
        await ctx.message.add_reaction(emoji='😔')
        return

    raise error

def loadtoken():
    global bot_token
    # load globals defined in the config file
    try:
        with open('configs/BOT_TOKEN') as f:
            print('loading token file for main bot')
            bot_token = f.readline()
            return True
    except:
        bot_token = os.environ.get('bot_token')
        return True

    if not loadtoken():
        exit()

if __name__ == '__main__':
    loadtoken()

    for cog in COGS:
        try:
            bot.load_extension(cog)
            print('Cog {} loaded.'.format(cog))
        except Exception as e:
            print('Cog {} failed to load.'.format(cog))
            traceback.print_exc()

    bot.state = "run"
    bot.run(bot_token)