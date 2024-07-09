#https://stackoverflow.com/questions/71165431/how-do-i-make-a-working-slash-command-in-discord-py
import discord
import json
from discord import app_commands
from photoshop import Session
import photoshop.api as ps
import sqlite3

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
settingsFile= open('settings.json')
settings=json.load(settingsFile)
con = sqlite3.connect("data.db")
con.row_factory = sqlite3.Row

#region Database management
def create_tables():
    sql_statements = [ 
        """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                discord_id INTEGER
        );""",
        """CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY,
                skill_name  TEXT DEFAULT "" NOT NULL,
                skill_desc  TEXT DEFAULT "" NOT NULL,
                spe1 INTEGER,
                spe2 INTEGER,
                spe3 INTEGER
        );""",
        """CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY,
                card_name TEXT DEFAULT "" NOT NULL,
                cp_name TEXT DEFAULT "" NOT NULL, 
                owner_name TEXT DEFAULT "" NOT NULL,
                owner_cohort TEXT DEFAULT "" NOT NULL, 
                card_description TEXT DEFAULT "" NOT NULL, 
                bottom_text TEXT DEFAULT "" NOT NULL,
                cp_value INTEGER DEFAULT 0 NOT NULL,
                card_background INTEGER DEFAULT 0 NOT NULL,
                card_watermark INTEGER DEFAULT 0 NOT NULL,
                skill1_id INTEGER NOT NULL,
                skill2_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                FOREIGN KEY(skill1_id) REFERENCES skills(id),
                FOREIGN KEY(skill2_id) REFERENCES skills(id),
                FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
        );""",
        #A whitelist entry means that a user can modify a card, even if he's not the admin
        """CREATE TABLE IF NOT EXISTS whitelist_entry (
                user_id INTEGER,
                card_id INTEGER,
                PRIMARY KEY(user_id,card_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE
        );""",
        """CREATE TABLE IF NOT EXISTS server_settings (
                server_id INTEGER PRIMARY KEY,
                card_watermark INTEGER,
                server_cohort TEXT
        );"""
        ]
    cur=con.cursor()
    for statement in sql_statements:
        cur.execute(statement)

create_tables()

def get_or_create_user(discordId):
    cursor = con.cursor()
    cursor.execute("SELECT * from users WHERE discord_id=?",(discordId,))
    result=cursor.fetchone()
    if(result!=None): return result

    cursor=con.cursor()
    cursor.execute("INSERT INTO users (discord_id) VALUES (?)",(discordId,))
    cursor.execute("SELECT * from users WHERE discord_id=?",(discordId,))
    con.commit()
    result=cursor.fetchone()
    return result

def get_or_create_card(user):
    for userKey in user.keys():
        print(str(userKey)+" "+str(user[userKey]))
    # for userKey in user:
    #     print(str(userKey))
    cursor=con.cursor()
    cursor.execute("SELECT * from cards WHERE owner_id=?",(user["id"],))
    result=cursor.fetchone()
    if(result!=None): return sqlite3Row_to_dict(result)

    cursor=con.cursor()
    cursor.execute("""INSERT INTO skills (skill_name) VALUES("Skill 1")""")
    skill1_id=cursor.lastrowid
    cursor.execute("""INSERT INTO skills (skill_name) VALUES("Skill 2")""")
    skill2_id=cursor.lastrowid

    cursor.execute("INSERT INTO cards (owner_id, skill1_id,skill2_id) VALUES (?,?,?)",(user["id"],skill1_id,skill2_id))
    con.commit()
    cursor.execute("SELECT * from cards WHERE owner_id=?",(user["id"],))
    result=cursor.fetchone()
    return sqlite3Row_to_dict(result)

def sqlite3Row_to_dict(sqlite3Row):
    dict={}
    for sqlite3Row_field in sqlite3Row.keys():
        dict[sqlite3Row_field]=sqlite3Row[sqlite3Row_field]
    return dict

def update_card(card):
    cursor=con.cursor()
    cursor.execute("""
                UPDATE cards 
                SET 
                    card_name=?
                WHERE
                    id=?
                """,(card["card_name"],card["id"]))
    con.commit()
#endregion

#region Photoshop management
app = ps.Application()

def create_psd_card(cardDatas):
    with Session(settings["TemplatePsdFile"], action="open", auto_close=True) as ps:
        nameLayer = ps.active_document.artLayers.getByName(settings["NameLayer"])
        assert nameLayer.name == settings["NameLayer"]
        nameLayer.textItem.contents = cardDatas["card_name"]

        #save the psd
        psd_file = settings["GeneratedPsdFolder"]+"/"+cardDatas["card_name"]+".psd"
        doc = ps.active_document
        options = ps.PhotoshopSaveOptions()
        doc.saveAs(psd_file, options, True)
        ps.alert("Task done!")
        ps.echo(doc.activeLayer)

        #export the pdf
        option = ps.PDFSaveOptions()
        option.jpegQuality = 12
        option.layers = True
        option.view = True  # opens the saved PDF in Acrobat.
        pdf = settings["ExportPngFolder"]+"/"+cardDatas["card_name"]+".pdf"
        ps.active_document.saveAs(pdf, option)

#endregion

#region Bot management
@tree.command(
    name="set",
    description="Set the value of one or more fields of your card",
    guild=discord.Object(id=790626187944394772)
)
async def set_card_field(interaction, name:str ):
    user=get_or_create_user(interaction.user.id)
    card=get_or_create_card(user)

    card["card_name"]=name
    update_card(card)

    for role in interaction.user.roles:
        print(role.name)
    
    await interaction.response.send_message("Hello "+interaction.user.name+" ! "+name)

@tree.command(
    name="get",
    description="Prints all the values of your card in a text format, quicker than a full preview",
    guild=discord.Object(id=790626187944394772)
)
async def get(interaction):
    user=get_or_create_user(interaction.user.id)
    card=get_or_create_card(user)
    returnValue=""
    for card_field in card.keys():
        returnValue+=f"{card_field}:{card[card_field]}\n\n"

    await interaction.response.send_message(returnValue)

@tree.command(
    name="preview",
    description="Exports your card as a pdf",
    guild=discord.Object(id=790626187944394772)
)
async def get(interaction):
    user=get_or_create_user(interaction.user.id)
    card=get_or_create_card(user)
    
    create_psd_card(card)
    await interaction.response.send_message("Done !")



@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=790626187944394772))

client.run(settings["Token"])
#endregion