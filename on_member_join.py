import discord

intents = discord.Intents.all()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print('logged in as {0.user}'.format(client))

@client.event
async def on_member_join(member):
    embed = discord.Embed(color=discord.Color.red())
    embed.set_author(name='{0.user}'.format(client), icon_url='https://scontent.fsyd1-1.fna.fbcdn.net/v/t1.15752-9/119154591_373692013645493_2520568812144261390_n.png?_nc_cat=100&ccb=2&_nc_sid=ae9488&_nc_ohc=qee8e9Q3a0sAX9_z2Nj&_nc_ht=scontent.fsyd1-1.fna&oh=ffeafaaa09f2bb802afce08030c41f08&oe=60394D0B')
    embed.add_field(name='WELCOME TO LINKED.GG', value='Looking forward to seeing you in queue!', inline=False)
    embed.add_field(name='Link your STEAM account to the bot:',
                    value='Reply to this bots message: \n `!login <steam profile url>`', inline=False)
    embed.add_field(name='Please read over the rules:',
                    value='<#804911670698442815>', inline=False)
    embed.add_field(name='Join our discord server', value='[Click here to play!](https://discord.gg/QAKb7sd3GY)', inline=True)
    await member.send(embed=embed)
    
client.run('')



















