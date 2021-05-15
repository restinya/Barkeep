import discord
import asyncio
import re
import collections
import d20
import requests

from time import sleep
from discord.ext import commands
from configs.settings import command_prefix
from utils import accessDB, point_buy, alpha_emojis, db, VerboseMDStringifier, traceBack, checkForChar

class Character(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        msg = None
        
        if isinstance(error, commands.BadArgument):
            # convert string to int failed
            msg = "Your stats and level need to be numbers. "

        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
             return
        elif isinstance(error, commands.CheckFailure):
            msg = "This channel or user does not have permission for this command. "
        elif isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == "name":
                msg = ":warning: You're missing the name for the character you want to create.\n"
            elif error.param.name == "level":
                msg = ":warning: You're missing a level for the character you want to create.\n"
            elif error.param.name == "race":
                msg = ":warning: You're missing a race for the character you want to create.\n"
            elif error.param.name == "c_class":
                msg = ":warning: You're missing a class for the character you want to create.\n"
            elif error.param.name == 'bg':
                msg = ":warning: You're missing a background for the character you want to create.\n"
            elif error.param.name == 'c_str' or  error.param.name == 'c_dex' or error.param.name == 'c_con' or error.param.name == 'c_int' or error.param.name == 'c_wis' or error.param.name == 'c_cha':
                msg = ":warning: You're missing a stat (STR, dex, con, int, wis, or cha) for the character you want to create.\n"
            elif error.param.name == 'magic_item':
                msg = ":warning: You're missing a free item of common or uncommon rarity.\n"
            elif error.param.name == 'url':
                msg = ":warning: You're missing a URL to add an image to your character's information window.\n"
            elif error.param.name == 'm':
                msg = ":warning: You're missing a magic item to attune to, or unattune from, your character.\n"

            msg += "**Note: if this error seems incorrect, something else may be incorrect.**\n\n"

        if msg:
            if ctx.command.name == "create":
                msg += f'Please follow this format:\n```yaml\n{command_prefix}create "name" level "race" "class" "background" STR dex con int wis cha "magic item"```\n'
            elif ctx.command.name == "info":
                msg += f'Please follow this format:\n```yaml\n{command_prefix}info "character name"```\n'
            elif ctx.command.name == "image":
                msg += f'Please follow this format:\n```yaml\n{command_prefix}image "character name" "URL"```\n'
            elif ctx.command.name == "levelup":
                msg += f'Please follow this format:\n```yaml\n{command_prefix}levelup "character name"```\n'
            elif ctx.command.name == "attune":
                msg += f'Please follow this format:\n```yaml\n{command_prefix}attune "character name" "magic item"```\n'
            elif ctx.command.name == "unattune":
                msg += f'Please follow this format:\n```yaml\n{command_prefix}unattune "character name" "magic item"```\n'
            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)


        elif isinstance(error, commands.CommandOnCooldown):
            return

        elif isinstance(error, commands.CommandInvokeError):
            msg = f'The command is not working correctly. Please try again and make sure the format is correct.'
            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)
            await traceBack(ctx,error, False)
        else:
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @commands.has_role('DM')
    @commands.command()
    async def create(self, ctx, name, level: int, race, c_class, bg, c_str: int, c_dex: int, c_con: int, c_int: int, c_wis: int, c_cha: int, magic_item=None, u_id=None):
        name = name.strip()
        character_cog = self.bot.get_cog('Character')
        level_creation = {
            'Lvl 1': [3],
            'DM': [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        }
        roles = [r.name for r in ctx.author.roles]
        author = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        char_embed = discord.Embed()
        char_embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        char_embed.set_footer(text="React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")
        char_embedmsg = None
        abi_names = ['str', 'dex', 'con', 'int', 'wis', 'cha']

        char_dict = {
          'UID': str(author.id),
          'name': name,
          'level': int(level),
          'hp': 0,
          'class': c_class,
          'class_data': [],
          'race': "",
          'background': bg,
          'ability': { 
            'str': int(c_str),
            'dex': int(c_dex),
            'con': int(c_con),
            'int': int(c_int),
            'wis': int(c_wis),
            'cha': int(c_cha),
          },
          'skillProficiencies': {},
          'resistances': [],
          'deity': 'Unknown',
          'alignment': 'Unknown',
          'gp': 0,
          'reputation' : 0,
          'renown': 0,
          'magicItems': 'None',
          'consumables': 'None',
          'feats': 'None',
          'inventory': {},
          'spellcasting': False,
          'spellbook': {}
        }

        if not name:
            await channel.send(content=":warning: The name of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return

        if not race:
            await channel.send(content=":warning: The race of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return

        if not c_class:
            await channel.send(content=":warning: The class of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return
        
        if not bg:
            await channel.send(content=":warning: The background of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return


        lvl = int(level)
        # Provides an error message at the end. If there are more than one, it will join msg.
        msg = ""

        # name should be less then 65 chars
        if len(name) > 64:
            msg += ":warning: Your character's name is too long! The limit is 64 characters.\n"

        # Reserved for regex, lets not use these for character names please
        invalid_chars = ["[", "]", "?", '"', "\\", "*", "$", "{", "+", "}", "^", ">", "<", "|"]

        for i in invalid_chars:
            if i in name:
                msg += f":warning: Your character's name cannot contain `{i}`. Please revise your character name.\n"

        if msg == "":
            player_collection = db.EncountersPlayers
            player_records = list(player_collection.find({"UID": str(author.id)}))
            if player_records != list() and len(player_records['characters']) >= player_records['max_characters']:
                msg += f":warning: You already have **{len(player_records['characters'])}** character(s) and may only have a maximum of {player_records['max_characters']}! You may not create a new character at this time.\n"

        if msg == "":
            query = name
            query = query.replace('(', '\\(')
            query = query.replace(')', '\\)')
            query = query.replace('.', '\\.')
            chara_collection = db.EncountersCharacters
            chara_records = list(chara_collection.find({"UID": str(author.id), "characters.name": {"$regex": query, '$options': 'i' }}))
            if chara_records != list():
                msg += f":warning: You already have a character by the name of **{name}**! Please use a different name.\n"
        #==================LEVEL CHECKING=====================
        level_set = []
        for d in level_creation.keys():
            if d in roles:
                level_set += level_creation[d]

        level_set = set(level_set)

        if lvl not in level_set:
            msg += f":warning: You cannot create a character of **{lvl}**! You do not have the correct role!\n"

        #==================STAT CHECKING======================
        # Point Buy
        if msg == "":
            stats_array = {'str': int(c_str), 'dex': int(c_dex), 'con': int(c_con), 'int': int(c_int), 'wis': int(c_wis), 'cha': int(c_cha)}
            point_buys = {
                1: -16,
                2: -12,
                3: -9,
                4: -6,
                5: -4,
                6: -2,
                7: -1,
                8: 0,
                9: 1,
                10: 2,
                11: 3,
                12: 4,
                13: 5,
                14: 7,
                15: 9,
                16: 12,
                17: 15,
                18: 19,
                19: 23,
                20: 28
            }
            total_points = 0
            for s in stats_array:
                    total_points += point_buys[stats_array[s]]

            if any([s < 6 for s in stats_array.values()]):
                msg += f":warning: You have at least one stat below the minimum of 6.\n"
            if any([s > 18 for s in stats_array.values()]):
                msg += f":warning: You have at least one stat above the maximum of 18.\n"
            if total_points != 27:
                msg += f":warning: Your stats do not add up to 27 using point buy ({total_points}/27). Remember that you must list your stats before applying racial modifiers! Please check your point allocation using this calculator: <https://chicken-dinner.com/5e/5e-point-buy.html>\n"
        
        #=======RACE CHECKING=======
        if msg == "":
            r_record, char_embed, char_embedmsg = await accessDB(ctx, char_embed, char_embedmsg, 'EncountersRaces', race)
            if char_embedmsg == "Fail":
                return
            if not r_record:
                msg += f'• {race} isn\'t on the list or it isn\'t allowed! Check your #encounters-rules and check your spelling and if you think this is an error, message Restinya.\n'
            else:
                char_dict['race'] = r_record['name']

        if msg == "":
            stats_array, char_embedmsg = await point_buy(ctx, stats_array, r_record, char_embed, char_embedmsg)
            if not stats_array:
                return
            char_dict['ability'] = stats_array
        #=======BACKGROUND CHECKING=======
        if msg == "":
            b_record, char_embed, char_embedmsg = await accessDB(ctx, char_embed, char_embedmsg, 'EncountersBackgrounds', bg)
            if char_embedmsg == "Fail":
                return
            if not b_record:
                msg += f'• {bg} isn\'t on the list or it isn\'t allowed! Check your #encounters-rules and check your spelling and if you think this is an error, message Restinya.\n'
            else:
                char_dict['background'] = b_record['name']

        #=======CLASS CHECKING=======
        class_stat = []
        c_record = []
        broke = []
        total_level = 0
        multi_level = 0

        if '/' in c_class:
            multiclass_list = c_class.replace(' ', '').split('/')

            for m in multiclass_list:
                multi_level = re.search('\d+', m)
                if not multi_level:
                    msg += f":warning: You are missing the level for your multiclass {m}. Please check your format.\n"

                    break
                multi_level = multi_level.group()
                multi_class, char_embed, char_embedmsg = await accessDB(ctx, char_embed, char_embedmsg, 'EncountersClasses', m[:len(m) - len(multi_level)])

                if not multi_class:
                    c_record = None
                    broke.append(m[:len(m) - len(multi_level)])

                class_dupe = False
                if (c_record or c_record==list()):
                    for c in c_record:
                        if c['name'] == multi_class['name']:
                            c['level'] = str(int(c['level']) + int(multi_level))
                            class_dupe=True
                            break
                
                    if not class_dupe:
                        c_record.append({'class': multi_class, 'name': multi_class['name'], 'level': int(multi_level), 'subclass': None, 'hp_rolled': []})
                        char_dict['class_data'].append({'name': multi_class['name'], 'level': int(multi_level), 'subclass': None, 'hp_rolled': []})
                        if 'spellsKnown' in multi_class:
                            char_dict['spellcasting'] = True
                    total_level += int(multi_level)
            
            if len(c_record) > 1:
                for m in c_record[1:]:
                    statReq = m['class']['multiclassRequirement']['ability']
                    print(statReq)
                    if statReq:
                        if len(statReq) >= 2:
                            req_fulfilled = False
                            for x in range(len(statReq)):
                                for i in statReq[x]:
                                    if char_dict['ability'][i] >= statReq[x][i]:
                                        req_fulfilled = True
                            if not req_fulfilled:
                                msg += f":warning: In order to multiclass to or from **{m['class']['name']}** you need at least one of **13 {' or '.join(x.upper() for x in set().union(*(d.keys() for d in statReq)))}**. Please check your ability scores.\n"
                        elif len(statReq[0]) < 2:
                            req_fulfilled = True
                            for i in statReq[0]:
                                if char_dict['ability'][i] < statReq[0][i]:
                                  req_fulfilled = False
                            if not req_fulfilled:
                                msg += f":warning: In order to multiclass to or from **{m['class']['name']}** you need at least **13 in {' and '.join(x.upper() for x in list(statReq[0].keys()))}**. Please check your ability scores.\n"
        
        else:
            single_class, char_embed, char_embedmsg = await accessDB(ctx, char_embed, char_embedmsg, 'EncountersClasses', c_class)
            if single_class:
                c_record.append({'class': single_class, 'name': single_class['name'], 'level': lvl, 'subclass': None, 'hp_rolled': []})
                char_dict['class_data'].append({'name': single_class['name'], 'level': lvl, 'subclass': None, 'hp_rolled': []})
                if 'spellsKnown' in single_class:
                    char_dict['spellcasting'] = True
            else:
                c_record = None
                broke.append(c_class)

        char_dict['class'] = ""
        if not multi_level and '/' in c_class:
            pass
        elif len(broke)>0:
            msg += f':warning: **{broke}** isn\'t on the list or it is banned! Check your #encounters-rules and check your spelling and if you think this is an error, message Restinya.\n'
        elif total_level != lvl and len(c_record) > 1:
            msg += ':warning: Your classes do not add up to the total level. Please double-check your multiclasses.\n'
        elif msg == "":
            #Subclasses
            for m in c_record:
                m['subclass'] = None
                class_name = "{} {}".format(m['class']['name'], m['level'])

                class_statname = f"{m['class']['name']}"

                if int(m['class']['subclassLevel']) <= int(m['level']) and msg == "":
                    subclasses_list = m['class']['subclasses']
                    subclass, char_embedmsg = await character_cog.choose_subclass(ctx, subclasses_list, m['class']['name'], char_embed, char_embedmsg)
                    if not subclass:
                        return

                    m['subclass'] = f'{class_name} ({subclass})' 
                    class_stat.append(f'{class_statname}-{subclass}')

                    if char_dict['class'] == "": 
                        char_dict['class'] = f'{class_name} ({subclass})'
                    else:
                        char_dict['class'] += f' / {class_name} ({subclass})'
                else:
                    class_stat.append(class_statname)
                    if char_dict['class'] == "": 
                        char_dict['class'] = class_name
                    else:
                        char_dict['class'] += f' / {class_name}'
        #=======SKILL PROFICIENCIES TIME=======
        if msg == "":
            def alphaEmbedCheck(r, u):
                sameMessage = False
                if char_embedmsg.id == r.message.id:
                    sameMessage = True
                return sameMessage and ((r.emoji in alpha_emojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author
            
            for i in list(b_record['skillProficiencies'][0].keys()):
                if i == 'choose':
                    skill_choices = b_record['skillProficiencies'][0]['choose']['from']
                    skill_choices = [x for x in skill_choices if x not in list(char_dict['skillProficiencies'].keys())]
                    alphaIndex = len(skill_choices)
                    skill_choice_string = ""
                    for num in range(len(skill_choices)):
                        skill_choice_string += f'{alpha_emojis[num]}: {skill_choices[num].capitalize()}\n'
                    try:
                        char_embed.add_field(name=f"Your background allows the choice of a skill proficiency. React below with the skill you would like to give proficiency.", value=skill_choice_string, inline=False)
                        if char_embedmsg:
                            await char_embedmsg.edit(embed=char_embed)
                        else: 
                            char_embedmsg = await channel.send(embed=char_embed)
                        await char_embedmsg.add_reaction('❌')
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                    except asyncio.TimeoutError:
                        await char_embedmsg.delete()
                        await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
                        self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None
                    else:
                        if tReaction.emoji == '❌':
                            await char_embedmsg.edit(embed=None, content=f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
                            await char_embedmsg.clear_reactions()
                            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                            return None, None
                    await char_embedmsg.clear_reactions()
                    char_embed.clear_fields()
                    char_dict['skillProficiencies'][skill_choices[alpha_emojis.index(tReaction.emoji)]] = True
                    skill_choices.pop(alpha_emojis.index(tReaction.emoji))
                else:
                    char_dict['skillProficiencies'][i] = True

            if 'choose' in c_record[0]['class']['skillProficiencies'][0]:
                skill_choices = list(c_record[0]['class']['skillProficiencies'][0]['choose'].keys())
                #remove already owned skills from choice list
                skill_choices = [x for x in skill_choices if x not in list(char_dict['skillProficiencies'].keys())]
                for i in range(c_record[0]['class']['skillProficiencies'][0]['count']):
                    alphaIndex = len(skill_choices)
                    skill_choice_string = ""
                    for num in range(len(skill_choices)):
                        skill_choice_string += f'{alpha_emojis[num]}: {skill_choices[num].capitalize()}\n'
                    try:
                        char_embed.add_field(name=f"Your class {c_record[0]['class']['name']} allows the choice of a skill proficiency. React below with the skill you would like to give proficiency.", value=skill_choice_string, inline=False)
                        if char_embedmsg:
                            await char_embedmsg.edit(embed=char_embed)
                        else: 
                            char_embedmsg = await channel.send(embed=char_embed)
                        await char_embedmsg.add_reaction('❌')
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                    except asyncio.TimeoutError:
                        await char_embedmsg.delete()
                        await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
                        self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None
                    else:
                        if tReaction.emoji == '❌':
                            await char_embedmsg.edit(embed=None, content=f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
                            await char_embedmsg.clear_reactions()
                            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                            return None, None
                    await char_embedmsg.clear_reactions()
                    char_embed.clear_fields()
                    char_dict['skillProficiencies'][skill_choices[alpha_emojis.index(tReaction.emoji)]] = True
                    skill_choices.pop(alpha_emojis.index(tReaction.emoji))

            if len(c_record)>1:
                for m in c_record[1:]:
                    if 'multiclassSkillProficiencies' in m['class']:
                        skill_choices = list(m['class']['multiclassSkillProficiencies'][0]['choose'].keys())
                        #remove already owned skills from choice list
                        skill_choices = [x for x in skill_choices if x not in list(char_dict['skillProficiencies'].keys())]
                        print(char_dict['skillProficiencies'])
                        for i in range(m['class']['multiclassSkillProficiencies'][0]['count']):
                            alphaIndex = len(skill_choices)
                            skill_choice_string = ""
                            for num in range(len(skill_choices)):
                                skill_choice_string += f'{alpha_emojis[num]}: {skill_choices[num].capitalize()}\n'
                            try:
                                char_embed.add_field(name=f"Your multiclass {m['class']['name']} allows the choice of a skill proficiency. React below with the skill you would like to give proficiency.", value=skill_choice_string, inline=False)
                                if char_embedmsg:
                                    await char_embedmsg.edit(embed=char_embed)
                                else: 
                                    char_embedmsg = await channel.send(embed=char_embed)
                                await char_embedmsg.add_reaction('❌')
                                tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                            except asyncio.TimeoutError:
                                await char_embedmsg.delete()
                                await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
                                self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                                return None, None
                            else:
                                if tReaction.emoji == '❌':
                                    await char_embedmsg.edit(embed=None, content=f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
                                    await char_embedmsg.clear_reactions()
                                    self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                                    return None, None
                            await char_embedmsg.clear_reactions()
                            char_embed.clear_fields()
                            char_dict['skillProficiencies'][skill_choices[alpha_emojis.index(tReaction.emoji)]] = True
                            skill_choices.pop(alpha_emojis.index(tReaction.emoji))
        #=======FINAL STAT ADJUSTMENTS=======
        if msg == "":
            #HP
            hp_records = []
            for c in c_record:
            #     # Wizards get 2 free spells per wizard level
            #     if cc['Class']['Name'] == "Wizard":
            #         char_dict['Free Spells'] = [6,0,0,0,0,0,0,0,0]
            #         fsIndex = 0
            #         for i in range (2, int(cc['Level']) + 1 ):
            #             if i % 2 != 0:
            #                 fsIndex += 1
            #             char_dict['Free Spells'][fsIndex] += 2

                hp_records.append({'level':c['level'], 'subclass': c['subclass'], 'name': c['class']['name'], 'max': c['class']['hitdie']['max'], 'avg':c['class']['hitdie']['avg']})

            if hp_records:
                char_dict['hp'] = await character_cog.calc_hp(ctx, char_embed, char_embedmsg, hp_records, char_dict, lvl)
        #=======TIME FOR STARTING EQUIPMENTS=======
        if msg == "":
            def alphaEmbedCheck(r, u):
                sameMessage = False
                if char_embedmsg.id == r.message.id:
                    sameMessage = True
                return sameMessage and ((r.emoji in alpha_emojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author

            if 'startingEquipment' in c_record[0]['class'] and msg == "":
                startEquipmentLength = 0
                inv_coll = db.EncountersShop
                if not char_embedmsg:
                    char_embedmsg = await channel.send(embed=char_embed)
                elif char_embedmsg == "Fail":
                    msg += ":warning: You have either cancelled the command or a value was not found."
                else:
                    await char_embedmsg.edit(embed=char_embed)

                for item in c_record[0]['class']['startingEquipment']:
                    seTotalString = ""
                    alphaIndex = 0
                    for seList in item:
                        seString = []
                        for elk, elv in seList.items():
                            if 'Pack' in elk:
                                seString.append(f"{elk} x1")
                            else:
                                seString.append(f"{elk} x{elv}")
                        seTotalString += f"{alpha_emojis[alphaIndex]}: {', '.join(seString)}\n"
                        alphaIndex += 1

                    await char_embedmsg.clear_reactions()
                    char_embed.add_field(name=f"Starting Equipment: {startEquipmentLength + 1} of {len(c_record[0]['class']['startingEquipment'])}", value=seTotalString, inline=False)
                    await char_embedmsg.edit(embed=char_embed)
                    if len(item) > 1:
                        for num in range(0,alphaIndex): await char_embedmsg.add_reaction(alpha_emojis[num])
                        await char_embedmsg.add_reaction('❌')
                        try:
                            tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                        except asyncio.TimeoutError:
                            await char_embedmsg.delete()
                            await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                            self.bot.get_command('create').reset_cooldown(ctx)
                            return 
                        else:
                            if tReaction.emoji == '❌':
                                await char_embedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                                await char_embedmsg.clear_reactions()
                                self.bot.get_command('create').reset_cooldown(ctx)
                                return 
                        startEquipmentItem = item[alpha_emojis.index(tReaction.emoji)]
                    else:
                        startEquipmentItem = item[0]

                    await char_embedmsg.clear_reactions()

                    seiString = ""
                    for seik, seiv in startEquipmentItem.items():
                        seiString += f"{seik} x{seiv}\n"
                        if "Pack" in seik:
                            pack_item = list(inv_coll.find({"name": seik}))[0]
                            seiString = f"{seik}:\n"
                            for pk, pv in pack_item['contains'][0].items():
                                char_dict['inventory'][pk] = pv
                                seiString += f"+ {pk} x{pv}\n"

                    char_embed.set_field_at(startEquipmentLength, name=f"Starting Equipment: {startEquipmentLength + 1} of {len(c_record[0]['class']['startingEquipment'])}", value=seiString, inline=False)
                    
                    for k,v in startEquipmentItem.items():
                        if 'Any' in k:
                            item_types = k.split('Any')[1].strip().split(' ')
                            mangled_query = { '$and' : []}
                            for i in item_types:
                                mangled_query['$and'].append({'type': { '$regex': i, '$options': 'i' } })
                            charInv = list(inv_coll.find(mangled_query))
                            charInv = sorted(charInv, key = lambda i: i['name']) 

                            typeEquipmentList = []
                            for i in range (0,int(v)):
                                charInvString = f"Please choose from the choices below for {k} {i+1}:\n"
                                alphaIndex = 0
                                charInv = list(filter(lambda c: 'Yklwa' not in c['name'] and 'Light Repeating Crossbow' not in c['name'] and 'Double-Bladed Scimitar' not in c['name'] and 'Oversized Longbow' not in c['name'], charInv))
                                for c in charInv:
                                    charInvString += f"{alpha_emojis[alphaIndex]}: {c['name']}\n"
                                    alphaIndex += 1

                                char_embed.set_field_at(startEquipmentLength, name=f"Starting Equipment: {startEquipmentLength+1} of {len(c_record[0]['class']['startingEquipment'])}", value=charInvString, inline=False)
                                await char_embedmsg.clear_reactions()
                                await char_embedmsg.add_reaction('❌')
                                await char_embedmsg.edit(embed=char_embed)

                                try:
                                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                                except asyncio.TimeoutError:
                                    await char_embedmsg.delete()
                                    await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
                                    self.bot.get_command('create').reset_cooldown(ctx)
                                    return 
                                else:
                                    if tReaction.emoji == '❌':
                                        await char_embedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA```")
                                        await char_embedmsg.clear_reactions()
                                        self.bot.get_command('create').reset_cooldown(ctx)
                                        return 
                                
                                
                                p = 0
                                for a in charInv:
                                    p+=1
                                typeEquipmentList.append(charInv[alpha_emojis.index(tReaction.emoji)]['name'])
                                typeCount = collections.Counter(typeEquipmentList)
                                typeString = ""
                                for tk, tv in typeCount.items():
                                    if tk in char_dict['inventory']:
                                        char_dict['inventory'][tk] += tv
                                    else:
                                        char_dict['inventory'][tk] = tv
                                
                                typeString += f"{tk} x{char_dict['inventory'][tk]}\n"

                            char_embed.set_field_at(startEquipmentLength, name=f"Starting Equipment: {startEquipmentLength+1} of {len(c_record[0]['class']['startingEquipment'])}", value=seiString.replace(f"{k} x{v}\n", typeString), inline=False)

                        elif 'Pack' not in k:
                            
                            if k in char_dict['inventory']:
                                char_dict['inventory'][k] += v
                            else:
                                char_dict['inventory'][k] = v
                                
                    startEquipmentLength += 1
                await char_embedmsg.clear_reactions()
                char_embed.clear_fields()

        if msg:
            if char_embedmsg and char_embedmsg != "Fail":
                await char_embedmsg.delete()
            elif char_embedmsg == "Fail":
                msg = ":warning: You have either cancelled the command or a value was not found."
            await ctx.channel.send(f'There were error(s) when creating your character:\n{msg}')

            self.bot.get_command('create').reset_cooldown(ctx)
            return 
        
        print(char_dict);
        await character_cog.display_char(ctx, char_embed, char_embedmsg, char_dict)

        if not char_embedmsg:
            char_embedmsg = await channel.send(embed=char_embed, content="**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel.")
        else:
            await char_embedmsg.edit(embed=char_embed, content="**Double-check** your character information.\nIf this is correct please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel.")

        
        def charCreateCheck(r, u):
            sameMessage = False
            if char_embedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author


        if not char_embedmsg:
            char_embedmsg = await channel.send(embed=char_embed, content="**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel. ")
        else:
            await char_embedmsg.edit(embed=char_embed, content="**Double-check** your character information.\nIf this is correct please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel. ")

        await char_embedmsg.add_reaction('✅')
        await char_embedmsg.add_reaction('❌')
        try:
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=charCreateCheck , timeout=60)
        except asyncio.TimeoutError:
            await char_embedmsg.delete()
            await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
            self.bot.get_command('create').reset_cooldown(ctx)
            return
        else:
            await char_embedmsg.clear_reactions()
            if tReaction.emoji == '❌':
                await char_embedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA ```")
                await char_embedmsg.clear_reactions()
                self.bot.get_command('create').reset_cooldown(ctx)
                return

        try:
            chara_collection.insert_one(char_dict)
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            char_embedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
            print('Success')
            if char_embedmsg:
                await char_embedmsg.clear_reactions()
                await char_embedmsg.edit(embed=char_embed, content =f"Congratulations! :tada: You have created **{char_dict['name']}**!")
            else: 
                char_embedmsg = await channel.send(embed=char_embed, content=f"Congratulations! You have created your **{char_dict['name']}**!")

        self.bot.get_command('create').reset_cooldown(ctx)
        
    #TODO: LEVELUP
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @commands.has_role("DM")
    @commands.command(aliases=['lvl', 'lvlup', 'lv'])
    async def levelup(self, ctx, char):
        pass

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @commands.command(aliases=['img'])
    async def image(self,ctx, char, url):

        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        char_embed = discord.Embed()

        info_records, char_embedmsg = await checkForChar(ctx, char, char_embed)

        if info_records:
            charID = info_records['_id']
            data = {
                'image': url
            }

            try:
                r = requests.head(url)
                if r.status_code != requests.codes.ok:
                    await ctx.channel.send(content=f'It looks like the URL is either invalid or contains a broken image. Please follow this format:\n```yaml\n{command_prefix}image "character name" URL```\n') 
                    return
            except:
                await ctx.channel.send(content=f'It looks like the URL is either invalid or contains a broken image. Please follow this format:\n```yaml\n{command_prefix}image "character name" URL```\n') 

                return
              
            try:
                chara_collection = db.EncountersCharacters
                chara_collection.update_one({'_id': charID}, {"$set": data})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                char_embedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
            else:
                print('Success')
                await ctx.channel.send(content=f'I have updated the image for ***{char}***. Please double-check using one of the following commands:\n```yaml\n{command_prefix}info "character name"\n{command_prefix}char "character name"\n{command_prefix}i "character name"```')


    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @commands.command(aliases=['i', 'char'])
    async def info(self,ctx, char):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        char_embed = discord.Embed()
        char_embedmsg = None
        character_cog = self.bot.get_cog('Character')

        
        statusEmoji = ""
        char_dict, char_embedmsg = await checkForChar(ctx, char, char_embed)
        if char_dict:
            footer = f"We hope you've been enjoying your time on the server!"
            await character_cog.display_char(ctx, char_embed, char_embedmsg, char_dict)
            char_embed.set_footer(text=footer)

            if 'image' in char_dict:
                char_embed.set_thumbnail(url=char_dict['image'])

            if not char_embedmsg:
                char_embedmsg = await ctx.channel.send(embed=char_embed)
            else:
                await char_embedmsg.edit(embed=char_embed)

            self.bot.get_command('info').reset_cooldown(ctx)

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @commands.command()
    async def align(self,ctx, char, *, new_align):
        if( len(new_align) > 20 or len(new_align) <1):
            await ctx.channel.send(content=f'The new alignment must be between 1 and 20 symbols.')
            return

    
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        char_embed = discord.Embed()

        info_records, char_embedmsg = await checkForChar(ctx, char, char_embed)

        if info_records:
            charID = info_records['_id']
            data = {
                'alignment': new_align
            }

            try:
                playersCollection = db.players
                playersCollection.update_one({'_id': charID}, {"$set": data})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                char_embedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
            else:
                print('Success')
                await ctx.channel.send(content=f'I have updated the alignment for ***{info_records["name"]}***. Please double-check using one of the following commands:\n```yaml\n{command_prefix}info "character name"\n{command_prefix}char "character name"\n{command_prefix}i "character name"```')


    async def display_char(self, ctx, char_embed, char_embedmsg, char_dict):
        char_embed.clear_fields()    
        char_embed.title = f"{char_dict['name']} (Lv {char_dict['level']})"
        char_embed.description = f"**Race**: {char_dict['race']}\n**Class**: {char_dict['class']}\n**Background**: {char_dict['background']}\n**Max HP**: {char_dict['hp']}\n**GP**: {char_dict['gp']}"
        if char_dict['magicItems'] != 'None':
            char_embed.add_field(name='Magic Items', value=char_dict['magicItems'], inline=False)
        if char_dict['consumables'] != 'None':
            char_embed.add_field(name='Consumables', value=char_dict['consumables'], inline=False)
        char_embed.add_field(name='Renown', value=char_dict['renown'], inline=True)
        char_embed.add_field(name='Reputation', value=char_dict['reputation'], inline=True)
        char_embed.add_field(name='Feats', value=char_dict['feats'], inline=True)
        char_embed.add_field(name='Stats', value=f"**STR**: {char_dict['ability']['str']} **DEX**: {char_dict['ability']['dex']} **CON**: {char_dict['ability']['con']} **INT**: {char_dict['ability']['int']} **WIS**: {char_dict['ability']['wis']} **CHA**: {char_dict['ability']['cha']}", inline=False)
        skill_prof_string = ""
        for k in char_dict['skillProficiencies'].keys():
            skill_prof_string += f"• {k.capitalize()}\n"
        char_embed.add_field(name='Skill Proficiencies', value=skill_prof_string, inline=False)
        char_inv_string = ""
        if char_dict['inventory'] != "None":
            for k,v in char_dict['inventory'].items():
                char_inv_string += f"• {k} x{v}\n"
            char_embed.add_field(name='Current Inventory', value=char_inv_string, inline=False)
            char_embed.set_footer(text= char_embed.Empty)
    
    # async def point_buy(self, ctx, stats_array, r_record, char_embed, char_embedmsg):
    #     author = ctx.author
    #     channel = ctx.channel

    #     def confirmCheck(r, u):
    #         same_message = False
    #         if char_embedmsg.id == r.message.id:
    #             same_message = True
    #         return same_message and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author

    #     def slashCharEmbedcheck(r, u):
    #         same_message = False
    #         if char_embedmsg.id == r.message.id:
    #             same_message = True
    #         return same_message and ((r.emoji in alpha_emojis[:len(unique_array)]) or (str(r.emoji) == '❌')) and u == author

    #     if r_record:
    #         stats_bonus = r_record['ability'][0]

    #         if 'choose' in stats_bonus:
    #             unique_array = stats_bonus['choose']['from']
    #             for i in range(stats_bonus['choose']['count']):
    #                 skill_choice_string = ""
    #                 for num in range(len(unique_array)):
    #                     skill_choice_string += f'{alpha_emojis[num]}: {unique_array[num].upper()}\n'
    #                 try:
    #                     char_embed.add_field(name=f"The {r_record['name']} race lets you choose between the following stats. React below with the stat(s) you would like to choose.", value=skill_choice_string, inline=False)
    #                     if char_embedmsg:
    #                         await char_embedmsg.edit(embed=char_embed)
    #                     else: 
    #                         char_embedmsg = await channel.send(embed=char_embed)
    #                     for num in range(0,len(unique_array)): await char_embedmsg.add_reaction(alpha_emojis[num])
    #                     await char_embedmsg.add_reaction('❌')
    #                     tReaction, tUser = await self.bot.wait_for("reaction_add", check=slashCharEmbedcheck, timeout=60)
    #                 except asyncio.TimeoutError:
    #                     await char_embedmsg.delete()
    #                     await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
    #                     self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
    #                     return None, None
    #                 else:
    #                     if tReaction.emoji == '❌':
    #                         await char_embedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}char {ctx.invoked_with}```")
    #                         await char_embedmsg.clear_reactions()
    #                         self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
    #                         return None, None
    #                 await char_embedmsg.clear_reactions()
    #                 char_embed.clear_fields()
    #                 stats_bonus[unique_array[alpha_emojis.index(tReaction.emoji)]] = stats_bonus['choose'].get('amount') or 1
    #                 unique_array.pop(alpha_emojis.index(tReaction.emoji))
    #             del stats_bonus['choose']

    #         try:
    #             char_embed.add_field(name=f"This server allows the use of the Origin Customization optional rule from Tasha's. If you wish to do customize your ability scores, please react with ✅ else ❌ to proceed with standard ability scores.", value="✅: Customize Scores\n❌: Standard Scores", inline=False)
    #             if char_embedmsg:
    #                 await char_embedmsg.edit(embed=char_embed)
    #             else: 
    #                 char_embedmsg = await channel.send(embed=char_embed)
    #             await char_embedmsg.add_reaction('✅')
    #             await char_embedmsg.add_reaction('❌')
    #             tReaction, tUser = await self.bot.wait_for("reaction_add", check=confirmCheck, timeout=60)
    #         except asyncio.TimeoutError:
    #             await char_embedmsg.delete()
    #             await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
    #             self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
    #             return None, None
    #         else:
    #             if tReaction.emoji == '✅':
    #                 await char_embedmsg.clear_reactions()
    #                 char_embed.clear_fields()
    #                 unique_array = ['str', 'dex', 'con', 'int', 'wis', 'cha']
    #                 bonuses = stats_bonus.values()
    #                 print(bonuses)
    #                 stats_bonus = {}
    #                 for i in bonuses:
    #                     skill_choice_string = ""
    #                     for num in range(len(unique_array)):
    #                         skill_choice_string += f'{alpha_emojis[num]}: {unique_array[num].upper()}\n'
    #                     try:
    #                         char_embed.add_field(name=f"React below with the stat you would like to give +{i}.", value=skill_choice_string, inline=False)
    #                         if char_embedmsg:
    #                             await char_embedmsg.edit(embed=char_embed)
    #                         else: 
    #                             char_embedmsg = await channel.send(embed=char_embed)
    #                         for num in range(0,len(unique_array)): await char_embedmsg.add_reaction(alpha_emojis[num])
    #                         await char_embedmsg.add_reaction('❌')
    #                         tReaction, tUser = await self.bot.wait_for("reaction_add", check=slashCharEmbedcheck, timeout=60)
    #                     except asyncio.TimeoutError:
    #                         await char_embedmsg.delete()
    #                         await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
    #                         self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
    #                         return None, None
    #                     else:
    #                         if tReaction.emoji == '❌':
    #                             await char_embedmsg.edit(embed=None, content=f'Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR dex con int wis cha```')
    #                             await char_embedmsg.clear_reactions()
    #                             self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
    #                             return None, None
    #                     await char_embedmsg.clear_reactions()
    #                     char_embed.clear_fields()
    #                     stats_bonus[unique_array[alpha_emojis.index(tReaction.emoji)]] = i
    #                     unique_array.pop(alpha_emojis.index(tReaction.emoji))

    #             if tReaction.emoji == '❌':
    #                 await char_embedmsg.clear_reactions()
    #                 char_embed.clear_fields()
            
    #         print(stats_array)
    #         print(stats_bonus)
    #         if 'str' in stats_bonus:
    #             stats_array['str'] += stats_bonus['str']
    #             # unique_array.remove('str')
    #         if 'dex' in stats_bonus:
    #             stats_array['dex'] += stats_bonus['dex']
    #             # unique_array.remove('dex')
    #         if 'con' in stats_bonus:
    #             stats_array['con'] += stats_bonus['con']
    #             # unique_array.remove('con')
    #         if 'int' in stats_bonus:
    #             stats_array['int'] += stats_bonus['int']
    #             # unique_array.remove('int')
    #         if 'wis' in stats_bonus:
    #             stats_array['wis'] += stats_bonus['wis']
    #             # unique_array.remove('wis')
    #         if 'cha' in stats_bonus:
    #             stats_array['cha'] += stats_bonus['cha']
    #             # unique_array.remove('cha')

    #         print(stats_array)
    #         return stats_array, char_embedmsg

    async def choose_subclass(self, ctx, subclassesList, charClass, char_embed, char_embedmsg):
        author = ctx.author
        channel = ctx.channel
        def classEmbedCheck(r, u):
            sameMessage = False
            if char_embedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((r.emoji in alpha_emojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author

        try:
            subclassString = ""
            for num in range(len(subclassesList)):
                subclassString += f'{alpha_emojis[num]}: {subclassesList[num]}\n'

            char_embed.clear_fields()
            char_embed.add_field(name=f"The {charClass} class allows you to pick a subclass at this level. React to the choices below to select your subclass.", value=subclassString, inline=False)
            alphaIndex = len(subclassesList)
            if char_embedmsg:
                await char_embedmsg.edit(embed=char_embed)
            else: 
                char_embedmsg = await channel.send(embed=char_embed)
            await char_embedmsg.add_reaction('❌')
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=classEmbedCheck, timeout=60)
        except asyncio.TimeoutError:
            await char_embedmsg.delete()
            await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{command_prefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
            return None, None
        else:
            if tReaction.emoji == '❌':
                await char_embedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{command_prefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                await char_embedmsg.clear_reactions()
                self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                return None, None
        await char_embedmsg.clear_reactions()
        char_embed.clear_fields()
        choiceIndex = alpha_emojis.index(tReaction.emoji)
        subclass = subclassesList[choiceIndex].strip()

        return subclass, char_embedmsg

    async def calc_hp(self, ctx, char_embed, char_embedmsg, classes, char_dict, lvl):
        # classes = sorted(classes, key = lambda i: i['Hit Die Max'],reverse=True) 
        total_hp = 0
        total_hp += classes[0]['max']
        current_level = 1
        if not char_dict['class_data'][0]['hp_rolled']:
            char_dict['class_data'][0]['hp_rolled'].append(classes[0]['max'])
        for i in range(len(classes)):
            class_level = classes[i]['level']
            while current_level < int(class_level):
                char_embed.clear_fields()
                while len(char_dict['class_data'][i]['hp_rolled']) < int(class_level):
                        sleep(2)
                        res = d20.roll(f"d{classes[i]['max']}mi{classes[i]['avg']}", advantage=False, stringifier=VerboseMDStringifier())
                        char_embed.add_field(name=f"Rolling for {char_dict['class_data'][i]['name']} level {len(char_dict['class_data'][i]['hp_rolled'])+1}... ", value=str(res), inline=False)
                        if char_embedmsg:
                            await char_embedmsg.edit(embed=char_embed)
                        else: 
                            char_embedmsg = await ctx.channel.send(embed=char_embed)
                        char_dict['class_data'][i]['hp_rolled'].append(res.total)
                print(char_dict['class_data'])
                total_hp += char_dict['class_data'][i]['hp_rolled'][current_level]
                current_level += 1
            current_level = 0

        total_hp += ((char_dict['ability']['con'] - 10) // 2 ) * lvl
        
        # specialCollection = db.special
        # specialRecords = list(specialCollection.find())

        # for s in specialRecords:
        #     if s['Type'] == "Race" or s['Type'] == "Feats" or s['Type'] == "Magic Items":
                
        #         if s['Name'] in char_dict[s['Type']]:
        #             if 'HP' in s:
        #                 if 'Half Level' in s:
        #                     total_hp += s['HP'] * floor(lvl/2)
        #                 else:
        #                     total_hp += s['HP'] * lvl
        #     elif s['Type'] == "Class":
        #         for multi in char_dict['Class'].split("/"):
        #             multi = multi.strip()
        #             multi_split = list(multi.split(" "))
        #             class_level = lvl
        #             class_name = multi_split[0]
        #             if len(multi_split) > 2:
        #                 try:
        #                     class_level=int(multi_split.pop(1))
        #                 except Exception as e:
        #                     continue
        #             class_name = " ".join(multi_split)
                        
                        
        #             if class_name == s["Name"]:
                        
        #                 if 'HP' in s:
        #                     if 'Half Level' in s:
        #                         total_hp += s['HP'] * floor(class_level/2)
        #                     else:
        #                         total_hp += s['HP'] * class_level
        char_embed.clear_fields()
        return total_hp

    #TODO: FEATS
    async def choose_feat(self, ctx):
        pass

def setup(bot):
    bot.add_cog(Character(bot))