#https://stackoverflow.com/questions/71165431/how-do-i-make-a-working-slash-command-in-discord-py
import discord
import json
from discord import app_commands

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
settingsFile= open('settings.json')
settings=json.load(settingsFile)

@client.event
async def on_ready():
    await tree.sync()
    print("Ready!")

client.run(settings["Token"])