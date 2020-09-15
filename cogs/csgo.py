import discord
from discord.ext import commands
from random import randint
from datetime import date
import sqlite3
import valve.rcon
import valve.source.a2s
import asyncio
import traceback
import json
import bot

# TODO: Allow administrators to update the maplist
active_map_pool = ['de_inferno', 'de_train', 'de_mirage', 'de_nuke', 'de_overpass', 'de_dust2', 'de_vertigo']
reserve_map_pool = ['de_cache', 'de_cbble', 'cs_office', 'cs_agency']
current_map_pool = active_map_pool.copy()

emoji_bank = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

# Veto style 1 2 2 2 1, last two 1s are for if we are playing with coaches
player_veto = [1, 2, 2, 2, 1, 1, 1]


class CSGO(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['10man', 'setup','start','ready'],
                      help='This command takes the users in a voice channel and selects two random '
                           'captains. It then allows those captains to select the members of their '
                           'team in a 1 2 2 2 2 1 fashion. It then configures the server with the '
                           'correct config.', brief='Helps automate setting up a PUG')
    async def pug(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.UserInputError(message='You must be in a voice channel.')
        """ if len(ctx.author.voice.channel.members) < 10:
            raise commands.CommandError(message='There must be 10 members connected to the voice channel') """
        db = sqlite3.connect('./main.sqlite')
        cursor = db.cursor()
        not_connected_members = []

        await ctx.channel.purge(limit=100)
        
        for member in ctx.author.voice.channel.members:
            cursor.execute('SELECT 1 FROM users WHERE discord_id = ?', (str(member),))
            data = cursor.fetchone()
            if data is None:
                not_connected_members.append(member)
        if len(not_connected_members) > 0:
            error_message = ''
            for member in not_connected_members:
                error_message += f'<@{member.id}> '
            error_message += 'must connect their steam account with the command ```!login <Steam Profile URL> or <SteamID>```'
            raise commands.UserInputError(message=error_message)

        # TODO: Refactor this mess
        # TODO: Add a way to cancel
        #players = ctx.author.voice.channel.members.copy()
        players = [ctx.author] * 10
        emojis = emoji_bank.copy()
        del emojis[len(players) - 2:len(emojis)]
        emojis_selected = []
        team1 = []
        team2 = []
        team1_captain = players[randint(0, len(players) - 1)]
        team1.append(team1_captain)
        players.remove(team1_captain)
        team2_captain = players[randint(0, len(players) - 1)]
        team2.append(team2_captain)
        players.remove(team2_captain)

        current_team_player_select = 1

        current_captain = team1_captain
        player_veto_count = 0

        message = await ctx.send('**```Loading player selection...```**')
        for emoji in emojis:
            await message.add_reaction(emoji)

        while len(players) > 0:
            message_text = ''
            players_text = ''

            if current_team_player_select == 1:
                message_text += f'<@{team1_captain.id}>'
                current_captain = team1_captain
            elif current_team_player_select == 2:
                message_text += f'<@{team2_captain.id}>'
                current_captain = team2_captain

            message_text += f' **`select {player_veto[player_veto_count]} player(s)`**\n'
            message_text += 'You have 30 seconds to choose your player(s)\n'

            i = 0
            for player in players:
                players_text += f'{emojis[i]} - <@{player.id}>\n'
                i += 1
            embed = self.player_veto_embed(message_text=message_text, players_text=players_text, team1=team1,
                                           team1_captain=team1_captain, team2=team2, team2_captain=team2_captain)
            await message.edit(content=message_text, embed=embed)

            selected_players = 0
            seconds = 0
            while True:
                await asyncio.sleep(1)
                message = await ctx.fetch_message(message.id)

                for reaction in message.reactions:
                    users = await reaction.users().flatten()
                    if current_captain in users and selected_players < player_veto[player_veto_count] and not (
                            reaction.emoji in emojis_selected):
                        index = emojis.index(reaction.emoji)
                        if current_team_player_select == 1:
                            team1.append(players[index])
                        if current_team_player_select == 2:
                            team2.append(players[index])
                        emojis_selected.append(reaction.emoji)
                        del emojis[index]
                        del players[index]
                        selected_players += 1

                seconds += 1

                if seconds % 30 == 0:
                    for x in range(0, player_veto[player_veto_count]):
                        index = randint(0, len(players) - 1)
                        if current_team_player_select == 1:
                            team1.append(players[index])
                        if current_team_player_select == 2:
                            team2.append(players[index])
                        emojis_selected.append(emojis[index])
                        del emojis[index]
                        del players[index]
                        selected_players += 1

                if selected_players == player_veto[player_veto_count]:
                    if current_team_player_select == 1:
                        current_team_player_select = 2
                    elif current_team_player_select == 2:
                        current_team_player_select = 1
                    break

            player_veto_count += 1

        message_text = 'Game Loading'
        players_text = 'None'
        embed = self.player_veto_embed(message_text=message_text, players_text=players_text, team1=team1,
                                       team1_captain=team1_captain, team2=team2, team2_captain=team2_captain)
        await message.edit(content=message_text, embed=embed)

        team1_steamIDs = []
        team2_steamIDs = []

        team1_channel = await ctx.author.voice.channel.category.create_voice_channel(name=f'Team {team1_captain}',
                                                                                     user_limit=5)
        team2_channel = await ctx.author.voice.channel.category.create_voice_channel(name=f'Team {team2_captain}',
                                                                                     user_limit=5)

        for player in team1:
            await player.move_to(channel=team1_channel, reason=f'You are on {team1_captain}\'s Team')
            cursor.execute('SELECT steam_id FROM users WHERE discord_id = ?', (str(player),))
            data = cursor.fetchone()
            team1_steamIDs.append(data[0])

        for player in team2:
            await player.move_to(channel=team2_channel, reason=f'You are on {team2_captain}\'s Team')
            cursor.execute('SELECT steam_id FROM users WHERE discord_id = ?', (str(player),))
            data = cursor.fetchone()
            team2_steamIDs.append(data[0])

        maps_string = 'Map pool for veto: '
        for cs_map in current_map_pool:
            maps_string += f'{cs_map}, '

        #await ctx.send(maps_string[:-2])

        match_config = {
            'matchid': f'PUG {date.today().strftime("%d-%B-%Y")}',
            'num_maps': 1,
            'maplist': current_map_pool,
            'skip_veto': False,
            'veto_first': 'team1',
            'side_type': 'always_knife',
            'players_per_team': len(team2),
            'min_players_to_ready': 1,
            'team1': {
                'name': f'Team {team1_captain.display_name}',
                'tag': f'Team {team1_captain.display_name}',
                'flag': 'AU',
                'players': team1_steamIDs
            },
            'team2': {
                'name': f'Team {team2_captain.display_name}',
                'tag': f'Team {team2_captain.display_name}',
                'flag': 'AU',
                'players': team2_steamIDs
            }
        }

        with open('./match_config.json', 'w') as outfile:
            json.dump(match_config, outfile, ensure_ascii=False, indent=4)

        match_config_json = await ctx.send(file=discord.File('match_config.json', '../match_config.json'))
        #await ctx.send('If you are coaching, once you join the server, type .coach')
        await asyncio.sleep(0.3)
        valve.rcon.execute(bot.server_address, bot.RCON_password, 'exec triggers/get5')
        await self.connect(ctx)
        await asyncio.sleep(10)
        valve.rcon.execute(bot.server_address, bot.RCON_password,
                           f'get5_loadmatch_url "{match_config_json.attachments[0].url}"')

    @pug.error
    async def pug_error(self, ctx, error):
        if isinstance(error, commands.UserInputError):
            await ctx.send(error)
        elif isinstance(error, commands.CommandError):
            await ctx.send(error)
        traceback.print_exc(error)

    def player_veto_embed(self, message_text, players_text, team1, team1_captain, team2, team2_captain):
        team1_text = ''
        team2_text = ''
        for team1_player in team1:
            team1_text += f'<@{team1_player.id}>'
            if team1_player is team1_captain:
                team1_text += ' 👑'
            team1_text += '\n'
        for team2_player in team2:
            team2_text += f'<@{team2_player.id}>'
            if team2_player is team2_captain:
                team2_text += ' 👑'
            team2_text += '\n'

        embed = discord.Embed(color=0x03f0fc)
        embed.add_field(name=f'Team {team1_captain.display_name}', value=team1_text, inline=True)
        embed.add_field(name='Players', value=players_text, inline=True)
        embed.add_field(name=f'Team {team2_captain.display_name}', value=team2_text, inline=True)
        return embed

    @commands.command(help='This command creates a URL that people can click to connect to the server.',
                      brief='Creates a URL people can connect to')
    async def connect(self, ctx):
        with valve.source.a2s.ServerQuerier(bot.server_address, timeout=20) as server:
            info = server.info()
        embed = discord.Embed(title=info['server_name'], color=0xf4c14e)
        embed.set_thumbnail(url="https://cdn.cloudflare.steamstatic.com/steamcommunity/public/images/apps/730/69f7ebe2735c366c65c0b33dae00e12dc40edbe4.jpg")
        embed.add_field(name='__**📡Quick Connect**__',
                        value=f'steam://connect/{bot.server_address[0]}:{bot.server_address[1]}/{bot.server_password}',
                        inline=False)
        embed.add_field(name='__**📡Console Connect**__',
                        value=f'```connect {bot.server_address[0]}:{bot.server_address[1]}; password {bot.server_password}```',
                        inline=False)
        #embed.add_field(name='**📺GOTV:**')
        embed.add_field(name='Players', value=f'{info["player_count"]}/{info["max_players"]}', inline=True)
        embed.add_field(name='Map', value=info['map'], inline=True)
        await ctx.send(embed=embed)

    @commands.command(aliases=['maps'], help='This command allows the user to change the map pool. '
                                             'Must have odd number of maps. Use "active" or "reserve" for the respective map pools.',
                      brief='Changes map pool', usage='<lists of maps> or "active" or "reserve"')
    async def map_pool(self, ctx, *, args):
        global current_map_pool
        if args == 'active':
            current_map_pool = active_map_pool.copy()
        elif args == 'reserve':
            current_map_pool = reserve_map_pool.copy()
        else:
            current_map_pool = args.split().copy()


def setup(client):
    client.add_cog(CSGO(client))