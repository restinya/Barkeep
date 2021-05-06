from discord.ext import commands

# ------- COGS -------

COGS = [

]


class Barkeep(commands.Bot):
    def __init__(self, prefix, description=None, testing=False, **options):
        