#https://stackoverflow.com/questions/71165431/how-do-i-make-a-working-slash-command-in-discord-py
import discord
import json
from discord import app_commands

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
settingsFile= open('settings.json')
settings=json.load(settingsFile)
dataFile=open('data.json', 'r', encoding='utf-8')
data=json.load(dataFile)
dataFile.close()


@client.event
async def on_ready():
    await tree.sync()
    print("Ready!")
    data["test"]="Everything fine"
    save_data()

def save_data():
    file=open('data.json', 'w', encoding='utf-8')
    json.dump(data,file)
    file.close()

client.run(settings["Token"])