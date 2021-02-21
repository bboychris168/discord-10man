import logging
from logging.config import fileConfig

import aiohttp
import discord
from discord.ext import commands, tasks

from bot import Discord_10man


class Utils(commands.Cog):
    def __init__(self, bot: Discord_10man):
        fileConfig('logging.conf')
        self.logger = logging.getLogger(f'10man.{__name__}')
        self.logger.debug(f'Loaded {__name__}')

        self.bot: Discord_10man = bot
        self.check_update.start()

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def load(self, ctx: commands.Context, extension: str):
        self.logger.debug(f'{ctx.author}: {ctx.prefix}{ctx.invoked_with} {ctx.args[2:]}')
        extension = f'cogs.{extension}'
        msg = await ctx.send(f'Loading {extension}')
        ctx.bot.load_extension(f'{extension}')
        await msg.edit(content=f'Loaded {extension}')
        self.logger.debug(f'Loaded {extension} via command')

    @load.error
    async def load_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, ImportError) or isinstance(error, commands.ExtensionNotFound) \
                or isinstance(error, commands.CommandInvokeError):
            await ctx.send(':warning: Extension does not exist.')
            self.logger.warning('Extension does not exist')
        else:
            await ctx.send(str(error))
            self.logger.exception('load command exception')

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def unload(self, ctx: commands.Context, extension: str):
        self.logger.debug(f'{ctx.author}: {ctx.prefix}{ctx.invoked_with} {ctx.args[2:]}')
        if extension not in ctx.bot.cogs.keys():
            raise commands.CommandError(':warning: Extension does not exist.')
        extension = f'cogs.{extension}'
        msg = await ctx.send(f'Loading {extension}')
        ctx.bot.unload_extension(f'{extension}')
        await msg.edit(content=f'Unloaded {extension}')
        self.logger.debug(f'Unloaded {extension} via command')

    @unload.error
    async def unload_error(self, ctx: commands.Context, error):
        self.logger.debug(f'{ctx.author}: {ctx.prefix}{ctx.invoked_with} {ctx.args[2:]}')
        if isinstance(error, commands.CommandError):
            await ctx.send(str(error))
            self.logger.warning('Extension does not exist')
        self.logger.exception('unload command exception')

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def clear(self, ctx: commands.Context, amount: int):
        self.logger.debug(f'{ctx.author}: {ctx.prefix}{ctx.invoked_with} {ctx.args[2:]}')
        await ctx.channel.purge(limit=amount)
        self.logger.debug(f'Purged {amount} in {ctx.channel}')

    @clear.error
    async def clear_error(self, ctx: commands.Context, error):
        self.logger.debug(f'{ctx.author}: {ctx.prefix}{ctx.invoked_with} {ctx.args[2:]}')
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('Please specify an amount of messages to delete')
            self.logger.warning(f'{ctx.author} did not specify number of messages to delete.')
        self.logger.exception('clear command exception')

    @tasks.loop(hours=24)
    async def check_update(self):
        self.logger.info('Checking for update.')
        session = aiohttp.ClientSession()
        async with session.get('https://api.github.com/repos/yannickgloster/discord-10man/releases/latest') as resp:
            json = await resp.json()
            if self.bot.version < json['tag_name'][1:]:
                self.bot.logger.info(f'{self.bot.version} bot is out of date, please update to {json["tag_name"]}')
                embed = discord.Embed(title=f'Discord 10man Update {json["tag_name"]}', url=json["html_url"])
                embed.set_thumbnail(
                    url="https://repository-images.githubusercontent.com/286741783/1df5e700-e141-11ea-9fbc-338769809f24")
                embed.add_field(name='Release Notes', value=f'{json["body"]}', inline=False)
                embed.add_field(name='Download', value=f'{json["html_url"]}', inline=False)
                owner: discord.Member = (await self.bot.application_info()).owner
                await owner.send(embed=embed)
        await session.close()

    @commands.command(aliases=['version', 'v', 'a'], help='This command gets the bot information and version')
    async def about(self, ctx: commands.Context):
        self.logger.debug(f'{ctx.author}: {ctx.prefix}{ctx.invoked_with} {ctx.args[2:]}')
        embed = discord.Embed(color=0xff0000)
        embed.add_field(name=f'LINKED.GG v{self.bot.version}',
                        value=f'Built by <@378014902620520451>', inline=False)
        await ctx.send(embed=embed)
        self.logger.debug(f'{ctx.author} got bot about info.')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            embed = discord.Embed(color=discord.Color.red())
            embed.set_author(name='LINKED.GG', icon_url='https://scontent.fsyd1-1.fna.fbcdn.net/v/t1.15752-9/119154591_373692013645493_2520568812144261390_n.png?_nc_cat=100&ccb=2&_nc_sid=ae9488&_nc_ohc=qee8e9Q3a0sAX9_z2Nj&_nc_ht=scontent.fsyd1-1.fna&oh=ffeafaaa09f2bb802afce08030c41f08&oe=60394D0B')
            embed.add_field(name='WELCOME TO LINKED.GG', value='Looking forward to seeing you in queue!', inline=False)
            embed.add_field(name='Link your STEAM account to the bot:',
                            value='Reply to this bots message: \n `!login <steam profile url>`', inline=False)
            """ embed.add_field(name='Please read over the rules:',
                            value='<#804911670698442815>', inline=False)
            embed.add_field(name='Join our discord server', value='[Click here to play!](https://discord.gg/QAKb7sd3GY)', inline=True) """
            await member.send(embed=embed)
        except (discord.HTTPException, discord.Forbidden):
            self.logger.error(f'Could not send {member} a PM')


def setup(client):
    client.add_cog(Utils(client))
