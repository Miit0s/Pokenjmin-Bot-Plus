#https://stackoverflow.com/questions/71165431/how-do-i-make-a-working-slash-command-in-discord-py
import discord
import json
from discord import app_commands
from photoshop import Session
import photoshop.api as photoshop
import sqlite3
import os
from tempfile import mkdtemp
from PIL import Image

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
                bottom_text_title TEXT DEFAULT "Pré-prod" NOT NULL,
                bottom_text_content TEXT DEFAULT "" NOT NULL,
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
                    card_name=?,
                    owner_name=?,
                    cp_name=?,
                    card_description=?,
                    bottom_text_title=?,
                    bottom_text_content=?,
                    cp_value=?
                WHERE
                    id=?
                """,(card["card_name"],card["owner_name"],card["cp_name"],card["card_description"],card["bottom_text_title"],card["bottom_text_content"],card["cp_value"],card["id"]))
    con.commit()
#endregion

#region Photoshop management
#app = ps.Application()

#Get layer by path written as Group/Group/Layer, for exampel Infos/Name
def get_layer_by_path(ps, layerPath):
    subGroups=str(layerPath).split("/")
    if(len(subGroups)<=1):
        return ps.active_document.artLayers.getByName(layerPath)
    
    i=0
    layerGroup=ps.active_document
    while(i<len(subGroups)-1):
        layerGroup= layerGroup.layerSets.getByName(subGroups[i])
        i+=1

    return layerGroup.artLayers.getByName(subGroups[len(subGroups)-1])

#https://loonghao.github.io/photoshop-python-api/examples/#replace-images
def replace_image(ps, layerToReplace, input_file):
    active_layer = layerToReplace
    ps.active_document.activeLayer=active_layer
    bounds = active_layer.bounds
    replace_contents = ps.app.stringIDToTypeID("placedLayerReplaceContents")
    desc = ps.ActionDescriptor
    idnull = ps.app.charIDToTypeID("null")
    desc.putPath(idnull, input_file)
    ps.app.executeAction(replace_contents, desc)

    # replaced image.
    current_bounds = active_layer.bounds
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]

    current_width = current_bounds[2] - current_bounds[0]
    current_height = current_bounds[3] - current_bounds[1]
    new_size = width / current_width * 100
    active_layer.resize(new_size, new_size, ps.AnchorPosition.MiddleCenter)

def create_psd_card(cardDatas, fileName, cardImagesName, isPreview=False):
    print(os.getcwd())
    with Session(os.path.join(os.getcwd(),settings["TemplatePsdFile"]), action="open", auto_close=True) as ps:
        i=0

        previewWatermark=ps.active_document.layerSets.getByName(settings["PreviewLayerGroup"])
        previewWatermark.visible=isPreview
        
        ownerNameLayer = get_layer_by_path(ps,settings["OwnerNameLayer"])
        ownerNameLayer.textItem.contents = cardDatas["owner_name"]

        cardNameLayer = get_layer_by_path(ps,settings["CardNameLayer"])
        cardNameLayer.textItem.contents = cardDatas["card_name"]

        descriptionLayer = get_layer_by_path(ps,settings["DescriptionLayer"])
        descriptionLayer.textItem.contents = cardDatas["card_description"]

        cpNameLayer = get_layer_by_path(ps,settings["CPNameLayer"])
        cpNameLayer.textItem.contents = cardDatas["cp_name"]

        cpValueLayer = get_layer_by_path(ps,settings["CPValueLayer"])
        cpValueLayer.textItem.contents = str(cardDatas["cp_value"])

        bottomTextLayer = get_layer_by_path(ps,settings["BottomTextLayer"])
        bottomTextLayer.textItem.contents = "["+cardDatas["bottom_text_title"]+"] "+cardDatas["bottom_text_content"]

        cardImagePath=os.path.join(os.getcwd(),settings["CardImagesFolder"],cardImagesName)
        if os.path.exists(cardImagePath):
            cardImageLayer=get_layer_by_path(ps,settings["CardImageLayer"])
            replace_image(ps,cardImageLayer,cardImagePath)

        ownerPhotoPath=os.path.join(os.getcwd(),settings["OwnerPhotosFolder"],cardImagesName)
        if os.path.exists(ownerPhotoPath):
            ownerPhotoLayer=get_layer_by_path(ps,settings["OwnerPhotoLayer"])
            replace_image(ps,ownerPhotoLayer,ownerPhotoPath)

        if isPreview:
            option = ps.JPEGSaveOptions()
            option.quality=1
            #you can't change the "jpg" part of the export path (for jpeg for example), Photoshop would overwrite it
            jpegPath = os.path.join(mkdtemp(),fileName+".jpg")
            ps.active_document.saveAs(jpegPath, option)
            return jpegPath

        #export the pdf
        option = ps.PDFSaveOptions()
        option.jpegQuality = 12
        option.layers = True
        option.view = False  # opens the saved PDF in Acrobat.
        pdf = os.path.join(os.getcwd(),settings["ExportPngFolder"],fileName+".pdf")
        ps.active_document.saveAs(pdf, option)

        #save the psd
        # psd_file = os.path.join(os.getcwd(),settings["GeneratedPsdFolder"],fileName+".psd")
        # doc = ps.active_document
        # options = ps.PhotoshopSaveOptions()
        # doc.saveAs(psd_file, options, True)

#endregion

#region Bot management
@tree.command(
    name="set_card",
    description="Set the value of one or more fields of your card",
    guild=discord.Object(id=790626187944394772)
)
async def setCard(interaction, card_name:str=None, owner_name:str=None,cp_name:str=None, card_description:str=None, bottom_text_title:str=None, 
                  bottom_text_content:str=None, cp_value:int=None, card_image:discord.Attachment=None, owner_photo:discord.Attachment=None):
    user=get_or_create_user(interaction.user.id)
    card=get_or_create_card(user)
    feedbackMessage=""
    error=False

    if(card_name!=None): card["card_name"]=card_name
    if(owner_name!=None): card["owner_name"]=owner_name
    if(cp_name!=None): card["cp_name"]=cp_name
    if(card_description!=None): card["card_description"]=card_description
    if(bottom_text_title!=None): card["bottom_text_title"]=bottom_text_title
    if(bottom_text_content!=None): card["bottom_text_content"]=bottom_text_content
    if(cp_value!=None): card["cp_value"]=cp_value

    if(card_image!=None):
        if card_image.content_type.split("/")[0]!="image":
            await interaction.response.send_message("Error: Card Image was not an image", ephemeral=True)
            return
        bruteImagePath=os.path.join(mkdtemp(),"cached_"+card_image.filename)
        await card_image.save(bruteImagePath)
        try:
            with Image.open(bruteImagePath) as im:
                ratio= im.width/im.height
                if(abs(ratio-settings["CardImagesPreferredRatio"])>=0.005):
                    feedbackMessage+="card_image isn't in the preferred ratio "+str(settings["CardImagesPreferredRatio"])+" it may not fit as you wish, consider modifying the image to be in the preferred ratio with dimensions of, for example "+str(1080)+"\*"+str(1080*settings["CardImagesPreferredRatio"])+"\n"
                im.save(os.path.join(os.getcwd(),settings["CardImagesFolder"],str(interaction.user.id)+".png"))
        except:
            feedbackMessage+="There was an error converting the card_image, try exporting it to another format like png or jpg\n"
            error=True

    if(owner_photo!=None):
        if owner_photo.content_type.split("/")[0]!="image":
            await interaction.response.send_message("Error: Card Image was not an image", ephemeral=True)
            return
        bruteImagePath=os.path.join(mkdtemp(),"cached_"+owner_photo.filename)
        await owner_photo.save(bruteImagePath)
        try:
            with Image.open(bruteImagePath) as im:
                ratio= im.width/im.height
                if(abs(ratio-settings["OwnerPhotoPreferredRatio"])>=0.005):
                    feedbackMessage+="owner_photo isn't in the preferred ratio "+str(settings["OwnerPhotoPreferredRatio"])+" it may not fit as you wish, consider modifying the image to be in the preferred ratio with dimensions of, for example "+str(1080)+"\*"+str(1080*settings["OwnerPhotoPreferredRatio"])+"\n"
                im.save(os.path.join(os.getcwd(),settings["OwnerPhotosFolder"],str(interaction.user.id)+".png"))
        except:
            feedbackMessage+="There was an error converting the card_image, try exporting it to another format like png or jpg\n"
            error=True

    update_card(card)

    for role in interaction.user.roles:
        print(role.name)
    
    if(error==False):
        feedbackMessage+="All field successfully setted !"
        
    await interaction.response.send_message(feedbackMessage,ephemeral=True)

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

    await interaction.response.send_message(returnValue,ephemeral=True)

@tree.command(
    name="preview",
    description="Exports your card as a pdf",
    guild=discord.Object(id=790626187944394772)
)
async def preview(interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    user=get_or_create_user(interaction.user.id)
    card=get_or_create_card(user)
    
    fileName=interaction.user.name
    jpegPreviewPath=create_psd_card(card, fileName,str(interaction.user.id)+".png", True)
    os.chdir(os.path.dirname(jpegPreviewPath))
    await interaction.followup.send("",ephemeral=True,file=discord.File(jpegPreviewPath))



@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=790626187944394772))

client.run(settings["Token"])
#endregion