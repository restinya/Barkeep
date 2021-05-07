import discord
from discord.ext import commands
from discord.ext.commands import CommandNotFound, MissingPermissions

# ------- COGS -------

COGS = [

]


class Barkeep(commands.Bot):
    def __init__(self, prefix, description=None, testing=False, **options):
        super().__init__(prefix, help_command=help_command, description=description, **options)
        self.state = "init"

intents = discord.Intents(
    guilds=True, members=True, messages=True, reactions=True
)

bot = Barkeep(prefix=get_prefix, description=desc, pm_help=True,
    activity = discord.Game(name f'Finding next encounters... | {config.DEFAULT_PREFIX}help'),
    allowed_mentions=discord.AllowedMentions.none(), intents=intents)

@bot.event
async def on_ready():
    console.log(f'Logging in as {bot.user.name} {bot.user.id}\n')

@bot.event
async def on_resumed():
    console.log('Resumed.')

@bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.message.add_reaction(emoji='😔')
            return

        raise error

for cog in COGS:
    bot.load_extension(cog)

if __name__ == '__main__':
    bot.state = "run"
    bot.run(token)