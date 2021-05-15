import os
import json
import re
import discord
import asyncio
import math
import d20
import traceback

from discord.ext import commands
from configs.settings import db, command_prefix

async def traceBack (ctx,error,silent=False):
    ctx.command.reset_cooldown(ctx)
    etype = type(error)
    trace = error.__traceback__

    # the verbosity is how large of a traceback to make
    # more specifically, it's the amount of levels up the traceback goes from the exception source
    verbosity = 6

    # 'traceback' is the stdlib module, `import traceback`.
    lines = traceback.format_exception(etype,error, trace, verbosity)

    # format_exception returns a list with line breaks embedded in the lines, so let's just stitch the elements together
    traceback_text = ''.join(lines)

    restinya = ctx.guild.get_member(842782914114748436)

    if not silent:
        await restinya.send(f"```{traceback_text}```\n")
        await ctx.channel.send(f"Uh oh, looks like this is some unknown error I have ran into. {ctx.guild.get_member(842782914114748436).mention} has been notified.")
    raise error


async def accessDB(ctx, api_embed="", api_embedmsg=None, table=None, query=None, exact=False):
    """
    Returns the appropriate record found from database with given query and table.

        Parameters:
            ctx (Context): original user message
            api_embed (discord.Embed): the embed element that the calling function will be using
            api_embedmsg (discord.Embed): the message that will contain api_embed
            table (String): table name to search
            query (String): search query
            exact (bool): exact search query

        Returns:
            record: Matched record from database
            api_embed: state of current embed element
            api_embedmsg: the message containing the embed element
    """
    channel = ctx.channel
    author = ctx.author
    if query.strip() == "":
        return None, api_embed, api_embedmsg

    if table is None:
       return None, api_embed, api_embedmsg

    invalidChars = ["[", "]", "?", '"', "\\", "*", "$", "{", "}", "^", ">", "<", "|"]

    for i in invalidChars:
        if i in query:
            await channel.send(f":warning: Please do not use `{i}` in your query. Revise your query and retry the command.\n")
            return None, api_embed, api_embedmsg

    collection = db[table]

    query = query.strip()
    query = query.replace('(', '\\(')
    query = query.replace(')', '\\)')
    query = query.replace('+', '\\+')
    query = query.replace('.', '\\.')

    print(query)

    records = list(collection.find({"name": {"$regex": query, '$options': 'i' }}))
    #turn the query into a regex expression
    r = re.compile(query, re.IGNORECASE)
    #restore the original query
    query = query.replace("\\", "")

    #sort elements by either the name, or the first element of the name list in case it is a list
    def sortingEntryAndList(elem):
        if(isinstance(elem['name'], list)): 
            return elem['name'][0] 
        else:  
            return elem['name']
    
    #sort all items alphabetically 
    records = sorted(records, key = sortingEntryAndList)    
    #if no elements are left, return nothing
    if records == []:
        return None, api_embed, api_embedmsg
    else:
        #create a string to provide information about the items to the user
        info_string = ""
        query_limit = 15
        if (len(records) > 1):
            #limit items to query_limit
            for i in range(0, min(len(records), query_limit)):
                info_string += f"{alpha_emojis[i]}: {records[i]['name']}\n"

            #inform the user of the current information and ask for their selection of an item
            api_embed.add_field(name=f"There seems to be multiple results for \"**{query}**\"! Please choose the correct one.\nThe maximum number of results shown is {query_limit}. If the result you are looking for is not here, please react with ❌ and be more specific.", value=info_string, inline=False)
            
            if not api_embedmsg or api_embedmsg == "Fail":
                api_embedmsg = await channel.send(embed=api_embed)
            else:
                await api_embedmsg.edit(embed=api_embed)
            for num in range(0,min(len(records), query_limit)): await api_embedmsg.add_reaction(alpha_emojis[num])
            await api_embedmsg.add_reaction('❌')

            def api_embedCheck(r, u):
                same_message = False
                if api_embedmsg.id == r.message.id:
                    same_message = True
                return ((r.emoji in alpha_emojis[:min(len(records), query_limit)]) or (str(r.emoji) == '❌')) and u == author and same_message
            try:
                tReaction, tUser = await bot.wait_for("reaction_add", check=api_embedCheck, timeout=60)
            except asyncio.TimeoutError:
                #stop if no response was given within the timeframe and reenable the command
                await api_embedmsg.delete()
                await channel.send('Timed out! Try using the command again.')
                ctx.command.reset_cooldown(ctx)
                return None, api_embed, "Fail"
            else:
                #stop if the cancel emoji was given and reenable the command
                if tReaction.emoji == '❌':
                    await api_embedmsg.edit(embed=None, content=f"Command cancelled. Try using the command again.")
                    await api_embedmsg.clear_reactions()
                    ctx.command.reset_cooldown(ctx)
                    return None, api_embed, "Fail"
            api_embed.clear_fields()
            #return the selected item indexed by the emoji given by the user
            await api_embedmsg.clear_reactions()
            records = records[alpha_emojis.index(tReaction.emoji)]
        else:
            #if only 1 item was left, simply return it
            records = records[0]
            # return records[0], api_embed, api_embedmsg

        if 'subraces' in records and isinstance(records['subraces'], list):
            def api_embedCheck(r, u):
                same_message = False
                if api_embedmsg.id == r.message.id:
                    same_message = True
                return ((r.emoji in alpha_emojis[:min(len(records), query_limit)]) or (str(r.emoji) == '❌')) and u == author and same_message

            print("subraces found")
            info_string = ""
            for i in range(0, min(len(records['subraces']), query_limit)):
                info_string += f"{alpha_emojis[i]}: {records['subraces'][i]}\n"

            api_embed.add_field(name=f"{records['name']} has the following subraces! Please choose the correct one.\nThe maximum number of results shown is {query_limit}. If the result you are looking for is not here, please react with ❌ and contact @Restinya.", value=info_string, inline=False)
            if not api_embedmsg:
                api_embedmsg = await channel.send(embed=api_embed)
            else:
                await api_embedmsg.edit(embed=api_embed)
            for num in range(0,min(len(records['subraces']), query_limit)): await api_embedmsg.add_reaction(alpha_emojis[num])
            await api_embedmsg.add_reaction('❌')

            try:
                tReaction, tUser = await bot.wait_for("reaction_add", check=api_embedCheck, timeout=60)
            except asyncio.TimeoutError:
                #stop if no response was given within the timeframe and reenable the command
                await api_embedmsg.delete()
                await channel.send('Timed out! Try using the command again.')
                ctx.command.reset_cooldown(ctx)
                return None, api_embed, "Fail"
            else:
                #stop if the cancel emoji was given and reenable the command
                if tReaction.emoji == '❌':
                    await api_embedmsg.edit(embed=None, content=f"Command cancelled. Try using the command again.")
                    await api_embedmsg.clear_reactions()
                    ctx.command.reset_cooldown(ctx)
                    return None, api_embed, "Fail"
            api_embed.clear_fields()
            #return the selected item indexed by the emoji given by the user
            await api_embedmsg.clear_reactions()
            subrace_records = list(db['EncountersSubraces'].find({"name": {"$regex": records['subraces'][alpha_emojis.index(tReaction.emoji)], '$options': 'i' }}))[0]
            del records['subraces']
            merge_records(records, subrace_records)

        return records, api_embed, api_embedmsg



async def checkForChar(ctx, char, charEmbed="", authorCheck=None, mod=False, customError=False):
    channel = ctx.channel
    author = ctx.author
    guild = ctx.guild

    if authorCheck != None:
        author = authorCheck

    charactersCollection = db.EncountersCharacters

    query = char.strip()
    query = query.replace('(', '\\(')
    query = query.replace(')', '\\)')
    query = query.replace('.', '\\.')
    if mod == True:
        charRecords = list(charactersCollection.find({"Name": {"$regex": query, '$options': 'i' }})) 
    else:
        charRecords = list(charactersCollection.find({"UID": str(author.id), "name": {"$regex": query, '$options': 'i' }}))

    if charRecords == list():
        if not mod and not customError:
            await channel.send(content=f'I was not able to find your character named "**{char}**". Please check your spelling and try again.')
        ctx.command.reset_cooldown(ctx)
        return None, None

    else:
        if len(charRecords) > 1:
            infoString = ""
            charRecords = sorted(list(charRecords), key = lambda i : i ['name'])
            for i in range(0, min(len(charRecords), 9)):
                infoString += f"{alpha_emojis[i]}: {charRecords[i]['name']} ({guild.get_member(int(charRecords[i]['UID']))})\n"
            
            def infoCharEmbedcheck(r, u):
                sameMessage = False
                if charEmbedmsg.id == r.message.id:
                    sameMessage = True
                return ((r.emoji in alpha_emojis[:min(len(charRecords), 9)]) or (str(r.emoji) == '❌')) and u == author and sameMessage

            charEmbed.add_field(name=f"There seems to be multiple results for \"`{char}`\"! Please choose the correct character. If you do not see your character here, please react with ❌ and be more specific with your query.", value=infoString, inline=False)
            charEmbedmsg = await channel.send(embed=charEmbed)
            await charEmbedmsg.add_reaction('❌')

            try:
                tReaction, tUser = await bot.wait_for("reaction_add", check=infoCharEmbedcheck, timeout=60)
            except asyncio.TimeoutError:
                await charEmbedmsg.delete()
                await channel.send('Character information timed out! Try using the command again.')
                ctx.command.reset_cooldown(ctx)
                return None, None
            else:
                if tReaction.emoji == '❌':
                    await charEmbedmsg.edit(embed=None, content=f"Character information cancelled. Try again using the same command!")
                    await charEmbedmsg.clear_reactions()
                    ctx.command.reset_cooldown(ctx)
                    return None, None
            charEmbed.clear_fields()
            await charEmbedmsg.clear_reactions()
            return charRecords[alpha_emojis.index(tReaction.emoji[0])], charEmbedmsg

    return charRecords[0], None

def merge_records(base_record, sub_record):
    del sub_record['_id']
    del sub_record['index']

    for key in sub_record:
        if sub_record[key] is None:
            pass
        elif key == 'name':
            base_record[key] = f"{base_record[key]} ({sub_record[key]})"
        elif key == 'ability':
            if len(sub_record[key]) == 2: 
                base_record[key] = sub_record[key]
            else:
                base_record[key] = [base_record[key][0] | sub_record[key][0]]
        elif key == 'languageProficiencies':
            base_record[key] = [base_record[key][0] | sub_record[key][0]]
        elif key == 'resists':
            base_record[key] = list(set(base_record[key]) | set(sub_record[key]))
        elif key == 'skillProficiencies':
            base_record[key] = sub_record[key]
        
    return base_record

async def point_buy(ctx, stats_array, r_record, api_embed, api_embedmsg):
    author = ctx.author
    channel = ctx.channel

    def confirmCheck(r, u):
        same_message = False
        if api_embedmsg.id == r.message.id:
            same_message = True
        return same_message and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author

    def slashCharEmbedcheck(r, u):
        same_message = False
        if api_embedmsg.id == r.message.id:
            same_message = True
        return same_message and ((r.emoji in alpha_emojis[:len(unique_array)]) or (str(r.emoji) == '❌')) and u == author

    if r_record:
        stats_bonus = r_record['ability'][0]

        if 'choose' in stats_bonus:
            unique_array = stats_bonus['choose']['from']
            for i in range(stats_bonus['choose']['count']):
                statSplitString = ""
                for num in range(len(unique_array)):
                    statSplitString += f'{alpha_emojis[num]}: {unique_array[num].upper()}\n'
                try:
                    api_embed.add_field(name=f"The {r_record['name']} race lets you choose between the following stats. React below with the stat(s) you would like to choose.", value=statSplitString, inline=False)
                    if api_embedmsg:
                        await api_embedmsg.edit(embed=api_embed)
                    else: 
                        api_embedmsg = await channel.send(embed=api_embed)
                    for num in range(0,len(unique_array)): await api_embedmsg.add_reaction(alpha_emojis[num])
                    await api_embedmsg.add_reaction('❌')
                    tReaction, tUser = await bot.wait_for("reaction_add", check=slashCharEmbedcheck, timeout=60)
                except asyncio.TimeoutError:
                    await api_embedmsg.delete()
                    await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR dex con int wis cha```')
                    bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                    return None, None
                else:
                    if tReaction.emoji == '❌':
                        await api_embedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}char {ctx.invoked_with}```")
                        await api_embedmsg.clear_reactions()
                        bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None
                await api_embedmsg.clear_reactions()
                api_embed.clear_fields()
                stats_bonus[unique_array[alpha_emojis.index(tReaction.emoji)]] = stats_bonus['choose'].get('amount') or 1
                unique_array.pop(alpha_emojis.index(tReaction.emoji))
            del stats_bonus['choose']

        try:
            api_embed.add_field(name=f"This server allows the use of the Origin Customization optional rule from Tasha's. If you wish to do customize your ability scores, please react with ✅ else ❌ to proceed with standard ability scores.", value="✅: Customize Scores\n❌: Standard Scores", inline=False)
            if api_embedmsg:
                await api_embedmsg.edit(embed=api_embed)
            else: 
                api_embedmsg = await channel.send(embed=api_embed)
            await api_embedmsg.add_reaction('✅')
            await api_embedmsg.add_reaction('❌')
            tReaction, tUser = await bot.wait_for("reaction_add", check=confirmCheck, timeout=60)
        except asyncio.TimeoutError:
            await api_embedmsg.delete()
            await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR dex con int wis cha```')
            bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
            return None, None
        else:
            if tReaction.emoji == '✅':
                await api_embedmsg.clear_reactions()
                api_embed.clear_fields()
                unique_array = ['str', 'dex', 'con', 'int', 'wis', 'cha']
                bonuses = stats_bonus.values()
                stats_bonus = {}
                for i in bonuses:
                    statSplitString = ""
                    for num in range(len(unique_array)):
                        statSplitString += f'{alpha_emojis[num]}: {unique_array[num].upper()}\n'
                    try:
                        api_embed.add_field(name=f"React below with the stat you would like to give +{i}.", value=statSplitString, inline=False)
                        if api_embedmsg:
                            await api_embedmsg.edit(embed=api_embed)
                        else: 
                            api_embedmsg = await channel.send(embed=api_embed)
                        for num in range(0,len(unique_array)): await api_embedmsg.add_reaction(alpha_emojis[num])
                        await api_embedmsg.add_reaction('❌')
                        tReaction, tUser = await bot.wait_for("reaction_add", check=slashCharEmbedcheck, timeout=60)
                    except asyncio.TimeoutError:
                        await api_embedmsg.delete()
                        await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR dex con int wis cha```')
                        bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None
                    else:
                        if tReaction.emoji == '❌':
                            await api_embedmsg.edit(embed=None, content=f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR dex con int wis cha```')
                            await api_embedmsg.clear_reactions()
                            bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                            return None, None
                    await api_embedmsg.clear_reactions()
                    api_embed.clear_fields()
                    stats_bonus[unique_array[alpha_emojis.index(tReaction.emoji)]] = i
                    unique_array.pop(alpha_emojis.index(tReaction.emoji))

            if tReaction.emoji == '❌':
                await api_embedmsg.clear_reactions()
                api_embed.clear_fields()
        
        print(stats_array)
        print(stats_bonus)
        if 'str' in stats_bonus:
            stats_array['str'] += stats_bonus['str']
            # unique_array.remove('str')
        if 'dex' in stats_bonus:
            stats_array['dex'] += stats_bonus['dex']
            # unique_array.remove('dex')
        if 'con' in stats_bonus:
            stats_array['con'] += stats_bonus['con']
            # unique_array.remove('con')
        if 'int' in stats_bonus:
            stats_array['int'] += stats_bonus['int']
            # unique_array.remove('int')
        if 'wis' in stats_bonus:
            stats_array['wis'] += stats_bonus['wis']
            # unique_array.remove('wis')
        if 'cha' in stats_bonus:
            stats_array['cha'] += stats_bonus['cha']
            # unique_array.remove('cha')

        print(stats_array)
        return stats_array, api_embedmsg

class VerboseMDStringifier(d20.MarkdownStringifier):
    def _str_expression(self, node):
        return f"**{node.comment or 'Result'}**: {self._stringify(node.roll)}\n" \
               f"**Total**: {int(node.total)}"


number_emojis = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','0️⃣']
alpha_emojis = ['🇦','🇧','🇨','🇩','🇪','🇫','🇬','🇭','🇮','🇯','🇰',
'🇱','🇲','🇳','🇴','🇵','🇶','🇷','🇸','🇹','🇺','🇻','🇼','🇽','🇾','🇿']

class Barkeep(commands.Bot):
    def __init__(self, prefix, description=None, **options):
        super(Barkeep, self).__init__(prefix, help_command=None, description=description, **options)
        self.state = "init"

intents = discord.Intents(
    guilds=True, members=True, messages=True, reactions=True
)

bot = Barkeep(prefix=command_prefix, description=None, pm_help=True, activity = discord.Activity(name='Searching for more adventurers...', type=discord.ActivityType.playing), case_insensitive=True, allowed_mentions=discord.AllowedMentions.none(), intents=intents)