import discord
import json
from discord import app_commands
from photoshop import Session
import photoshop.api as photoshop
import sqlite3
import os
from tempfile import mkdtemp
from PIL import Image
import re
import xml.etree.ElementTree as ET
import math
from io import BytesIO

intents = discord.Intents.default()
intents.members=True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
settingsFile= open('settings.json', encoding="utf-8")
settings=json.load(settingsFile)
con = sqlite3.connect("data.db")
con.row_factory = sqlite3.Row

#region Database management
def create_tables():
    sql_statements = [ 
        """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                discord_id TEXT NOT NULL,
                guild_id INTEGER NOT NULL,
                overwrite_discord_id TEXT,
                legendary_user INTEGER DEFAULT 0 NOT NULL
        );""",
        """CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY,
                skill_name  TEXT DEFAULT "" NOT NULL,
                skill_desc  TEXT DEFAULT "" NOT NULL,
                skill_cost INTEGER DEFAULT 0 NOT NULL,
                spe1 INTEGER,
                spe2 INTEGER,
                spe3 INTEGER
        );""",
        """CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY,
                card_name TEXT DEFAULT "" NOT NULL,
                cp_name TEXT DEFAULT "" NOT NULL, 
                owner_name TEXT DEFAULT "" NOT NULL,
                card_description TEXT DEFAULT "" NOT NULL, 
                bottom_text_title TEXT DEFAULT "Pré-prod" NOT NULL,
                bottom_text_content TEXT DEFAULT "" NOT NULL,
                cp_value INTEGER DEFAULT 0 NOT NULL,
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
                default_spe INTEGER,
                server_cohort TEXT,
                default_watermark INTEGER
        );""",
        """CREATE TABLE IF NOT EXISTS role_settings (
                role_id INTEGER,
                server_id INTEGER,
                spe INTEGER,
                FOREIGN KEY(server_id) REFERENCES server_settings(server_id) ON DELETE CASCADE,
                PRIMARY KEY(server_id, role_id)
        );""",
        ]
    cur=con.cursor()
    for statement in sql_statements:
        cur.execute(statement)

create_tables()

def get_or_create_server_settings(serverId):
    cursor = con.cursor()
    cursor.execute("SELECT * from server_settings WHERE server_id=?",(serverId,))
    result=cursor.fetchone()
    if(result!=None): return sqlite3Row_to_dict(result)

    cursor=con.cursor()
    cursor.execute("INSERT INTO server_settings (server_id) VALUES (?)",(serverId,))
    cursor.execute("SELECT * from server_settings WHERE server_id=?",(serverId,))
    con.commit()
    result=cursor.fetchone()
    return sqlite3Row_to_dict(result)

def get_server_settings(serverId):
    cursor = con.cursor()
    cursor.execute("SELECT * from server_settings WHERE server_id=?",(serverId,))
    result=cursor.fetchone()
    return result

def update_server_settings(server_settings):
    cursor=con.cursor()
    cursor.execute("""
                UPDATE server_settings 
                SET 
                    card_watermark=?,
                    default_spe=?,
                    server_cohort=?
                WHERE
                    server_id=?
                """,(server_settings["card_watermark"],server_settings["default_spe"],server_settings["server_cohort"],server_settings["server_id"]))
    con.commit()

def get_or_create_role_settings(serverId, roleId):
    cursor = con.cursor()
    cursor.execute("SELECT * from role_settings WHERE server_id=? AND role_id=?",(serverId,roleId))
    result=cursor.fetchone()
    if(result!=None): return sqlite3Row_to_dict(result)

    cursor=con.cursor()
    cursor.execute("INSERT INTO role_settings (server_id, role_id) VALUES (?,?)",(serverId,roleId))
    cursor.execute("SELECT * from role_settings WHERE server_id=? AND role_id=?",(serverId,roleId))
    con.commit()
    result=cursor.fetchone()
    return sqlite3Row_to_dict(result)

def get_roles_settings(serverId, roleId):
    cursor = con.cursor()
    cursor.execute("SELECT * from role_settings WHERE server_id=? AND role_id=?",(serverId,roleId))
    result=cursor.fetchone()
    return result

def update_role_settings(role_settings):
    cursor=con.cursor()
    cursor.execute("""
                UPDATE role_settings 
                SET 
                    spe=?
                WHERE
                    server_id=? AND role_id=?
                """,(role_settings["spe"],role_settings["server_id"],role_settings["role_id"]))
    con.commit()

def get_or_create_user(discordId, guildId):
    cursor = con.cursor()
    cursor.execute("SELECT * from users WHERE discord_id=?",(discordId,))
    result=cursor.fetchone()
    if(result!=None): return sqlite3Row_to_dict(result)

    cursor=con.cursor()
    cursor.execute("INSERT INTO users (discord_id, guild_id) VALUES (?,?)",(discordId,guildId))
    cursor.execute("SELECT * from users WHERE discord_id=?",(discordId,))
    con.commit()
    result=cursor.fetchone()
    return sqlite3Row_to_dict(result)

def create_legendary_user():
    cursor = con.cursor()
    cursor.execute("SELECT count(*) AS count FROM users WHERE legendary_user=TRUE")
    nbrOfLegendaries=cursor.fetchone()["count"]

    id="leg"+str(nbrOfLegendaries)
    cursor = con.cursor()
    cursor.execute("INSERT INTO users (discord_id, guild_id, legendary_user) VALUES (?,?, TRUE)",(id,0))
    cursor.execute("SELECT * from users WHERE discord_id=?",(id,))
    con.commit()
    result=cursor.fetchone()
    return sqlite3Row_to_dict(result)

def list_legendary_cards():
    cursor=con.cursor()
    cursor.execute("SELECT users.discord_id, owner_name, card_name FROM cards INNER JOIN users ON cards.owner_id=users.id WHERE users.legendary_user==True")
    result=cursor.fetchall()
    return result

def get_user(discordId):
    cursor = con.cursor()
    cursor.execute("SELECT * from users WHERE discord_id=?",(discordId,))
    result=cursor.fetchone()
    return result

def update_user_guild(userId, guildId):
    cursor = con.cursor()
    cursor.execute("UPDATE users SET guild_id=? WHERE discord_id=?", (guildId,userId))
    con.commit()

def update_user_overwrite(userId, overwriteId):
    cursor = con.cursor()
    cursor.execute("UPDATE users SET overwrite_discord_id=? WHERE discord_id=?", (overwriteId, userId))
    con.commit()

def get_or_create_card(user, ignoreOverwrites:bool=False):
    # for userKey in user:
    #     print(str(userKey))
    userId=user["id"]

    if user["overwrite_discord_id"]!=None and ignoreOverwrites==False:
        userId=get_user(user["overwrite_discord_id"])["id"]

    cursor=con.cursor()
    cursor.execute("SELECT * from cards WHERE owner_id=?",(userId,))
    result=cursor.fetchone()
    if(result!=None): return sqlite3Row_to_dict(result)

    cursor=con.cursor()
    cursor.execute("""INSERT INTO skills (skill_name) VALUES("Skill 1")""")
    skill1_id=cursor.lastrowid
    cursor.execute("""INSERT INTO skills (skill_name) VALUES("Skill 2")""")
    skill2_id=cursor.lastrowid

    cursor.execute("INSERT INTO cards (owner_id, skill1_id,skill2_id) VALUES (?,?,?)",(userId,skill1_id,skill2_id))
    con.commit()
    cursor.execute("SELECT * from cards WHERE owner_id=?",(userId,))
    result=cursor.fetchone()
    return sqlite3Row_to_dict(result)

def get_owner_of_card(card):
    cursor=con.cursor()
    cursor.execute("SELECT * FROM cards INNER JOIN users ON cards.owner_id=users.id WHERE users.id=?",(card["owner_id"],))
    result=cursor.fetchone()
    return result

def get_discord_id_of_card(card):
    return get_owner_of_card(card)["discord_id"]

def get_skill_of_card(card, skillNbr):
    cursor=con.cursor()
    skillParameter="skill1_id"
    if(skillNbr==2):
        skillParameter="skill2_id"
    skillId=card[skillParameter]
    cursor.execute(f"SELECT * from skills WHERE id=?", (skillId,))
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

def update_skill(skill):
    cursor=con.cursor()
    cursor.execute("""
                UPDATE skills
                SET 
                    skill_name=?,
                    skill_desc=?,
                    skill_cost=?,
                    spe1=?,
                    spe2=?,
                    spe3=?
                WHERE
                    id=?
                """,(skill["skill_name"],skill["skill_desc"],skill["skill_cost"],skill["spe1"],skill["spe2"],skill["spe3"],skill["id"]))
    con.commit()

#return the spe of the user, which is the default server spe if no override exist for any role of the user
def get_spe_for_user(guildId, userRoles):
    server=get_or_create_server_settings(guildId)
    spe=server["default_spe"]
    for role in userRoles:
        role_settings=get_roles_settings(guildId,role.id)
        if role_settings==None: continue
        return role_settings["spe"]

    return spe

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
    sizeMultiplier=width / current_width   
    newHeight=sizeMultiplier*current_height
    if(newHeight<height):
        sizeMultiplier=height/current_height

    new_size = sizeMultiplier * 100
    active_layer.resize(new_size, new_size, ps.AnchorPosition.MiddleCenter)

def create_psd_card(cardDatas, cohort, spe, fileName, cardImagesName, isPreview=False):
    with Session(os.path.join(os.getcwd(),settings["TemplatePsdFile"]), action="open", auto_close=True) as ps:
        i=0

        previewWatermark=ps.active_document.layerSets.getByName(settings["PreviewLayerGroup"])
        previewWatermark.visible=isPreview
        
        ownerNameLayer = get_layer_by_path(ps,settings["OwnerNameLayer"])
        ownerNameLayer.textItem.contents = cardDatas["owner_name"]

        cardNameLayer = get_layer_by_path(ps,settings["CardNameLayer"])
        cardNameLayer.textItem.contents = cardDatas["card_name"]

        descriptionLayer = get_layer_by_path(ps,settings["DescriptionLayer"])
        descriptionLayer.textItem.contents = replacePingsByCardNames(cardDatas["card_description"])

        cpNameLayer = get_layer_by_path(ps,settings["CPNameLayer"])
        cpNameLayer.textItem.contents = str(cardDatas["cp_name"]).upper()

        cpValueLayer = get_layer_by_path(ps,settings["CPValueLayer"])
        cpValueLayer.textItem.contents = str(cardDatas["cp_value"])

        bottomTextLayer = get_layer_by_path(ps,settings["BottomTextLayer"])
        bottomTextLayer.textItem.contents = "["+cardDatas["bottom_text_title"]+"] "+replacePingsByCardNames(cardDatas["bottom_text_content"])

        cardImagePath=os.path.join(os.getcwd(),settings["CardImagesFolder"],cardImagesName)
        if os.path.exists(cardImagePath):
            cardImageLayer=get_layer_by_path(ps,settings["CardImageLayer"])
            replace_image(ps,cardImageLayer,cardImagePath)

        ownerPhotoPath=os.path.join(os.getcwd(),settings["OwnerPhotosFolder"],cardImagesName)
        if os.path.exists(ownerPhotoPath):
            ownerPhotoLayer=get_layer_by_path(ps,settings["OwnerPhotoLayer"])
            replace_image(ps,ownerPhotoLayer,ownerPhotoPath)

        skill1Datas=get_skill_of_card(cardDatas,1)
        skill1LayerSet=ps.active_document.layerSets.getByName(settings["Skill1Group"])
        fill_layers_for_skill(ps,skill1LayerSet,skill1Datas)

        skill2Datas=get_skill_of_card(cardDatas,2)
        skill2LayerSet=ps.active_document.layerSets.getByName(settings["Skill2Group"])
        fill_layers_for_skill(ps,skill2LayerSet,skill2Datas)

        if(spe==None): spe=0

        speIconLayerGroup=ps.active_document.layerSets.getByName(settings["SpeIconGroupName"])
        set_spe_image(speIconLayerGroup,spe,"IconLayerName")

        backgroundLayerGroup=ps.active_document.layerSets.getByName(settings["BackgroundsGroupName"])
        set_spe_image(backgroundLayerGroup, spe,"BackgroundLayerName")

        cohortNameLayer = get_layer_by_path(ps,settings["CohortNameValueLayer"])
        cohortNameLayer.textItem.contents = cohort

        if isPreview:
            option = ps.JPEGSaveOptions()
            option.quality=1
            #you can't change the "jpg" part of the export path (for jpeg for example), Photoshop would overwrite it
            jpegPath = os.path.join(mkdtemp(),str(fileName)+".jpg")
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

def fill_layers_for_skill(ps, skillLayerGroup, skillDatas):
    skillDescLayer=skillLayerGroup.artLayers.getByName(settings["SkillDescLayerName"])
    skillDescLayer.textItem.contents=replacePingsByCardNames(skillDatas["skill_desc"])
    skillTitleLayer=skillLayerGroup.artLayers.getByName(settings["SkillTitleLayerName"])
    skillTitleLayer.textItem.contents=replacePingsByCardNames(skillDatas["skill_name"])
    skillCostLayer=skillLayerGroup.artLayers.getByName(settings["SkillCostLayerName"])
    skillCostLayer.textItem.contents=str(skillDatas["skill_cost"])

    spe1IconGroup=skillLayerGroup.layerSets.getByName(settings["Spe1IconGroupName"])
    set_spe_image(spe1IconGroup,skillDatas["spe1"],"IconLayerName")

    spe2IconGroup=skillLayerGroup.layerSets.getByName(settings["Spe2IconGroupName"])
    set_spe_image(spe2IconGroup,skillDatas["spe2"],"IconLayerName")

    spe3IconGroup=skillLayerGroup.layerSets.getByName(settings["Spe3IconGroupName"])
    set_spe_image(spe3IconGroup,skillDatas["spe3"],"IconLayerName")

    return

def set_spe_image(speIconsGroup, speId, imageLayerKey):
    chosenSpe=None
    for spe in settings["Specialties"]:
        if spe["Id"]==speId:
            chosenSpe=spe
            break
    
    if(chosenSpe==None):
        speIconsGroup.visible=False
        return

    for iconLayer in speIconsGroup.artLayers:
        iconLayer.visible=iconLayer.name==chosenSpe[imageLayerKey]
#endregion

#region SVG management
#app = ps.Application()

#Get layer by path written as Group/Group/Layer, for exampel Infos/Name
def get_svg_layer_by_path(root, layerPath):
    subGroups=str(layerPath).split("/")
    currentLayer=root
    if(" " in layerPath or "_" in layerPath):
        print("/!\\ Error: LayerPath that you want to get and modify cannot contain a \" \" or a \"_\"")

    for group in subGroups:
        nextLayer=None
        for child in currentLayer:
            if sanitizeTag(child.tag)!="g":continue
            if('id' not in child.attrib): continue
            if isSvgLayerEqual(child.attrib['id'],group):
                nextLayer=child
                break
        if(nextLayer==None):
            print("/!\\Couldn't find the layer "+layerPath)
        currentLayer=nextLayer
    return currentLayer

def change_text_of_svg_layer(layer,text):
    textDiv=None
    for child in layer:
        if sanitizeTag(child.tag)=="text":
            textDiv=child
            break
    if(textDiv==None):
        print("/!\\Couldn't find a text layer for  "+layer.attrib['id'])
    textDiv.text=text

def toggle_svg_layer_visibility(layer, visibility:bool):Z
    notVisibleString="display:none;"
    visibleString="display:inline;"

    desiredString=notVisibleString
    undesiredString=visibleString
    if(visibility):
        desiredString=visibleString
        undesiredString=notVisibleString

    if("style" not in layer.attrib):
        layer.attrib["style"]=desiredString
        return

    if(undesiredString in layer.attrib["style"]):
        layer.attrib["style"]=layer.attrib["style"].replace(undesiredString, desiredString)
        return
    
    if(desiredString in layer.attrib["style"]):
        returnZ
    
    layer.attrib["style"]=desiredString+layer.attrib["style"]

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
    sizeMultiplier=width / current_width   
    newHeight=sizeMultiplier*current_height
    if(newHeight<height):
        sizeMultiplier=height/current_height

    new_size = sizeMultiplier * 100
    active_layer.resize(new_size, new_size, ps.AnchorPosition.MiddleCenter)
    
#The tags are all prefixed by "{http://www.w3.org/2000/svg}", this function removes it
def sanitizeTag(input:str):
    return input.replace("{http://www.w3.org/2000/svg}","")

#Remove everything after a "_" in a layer id, keeping only the good part. But yes, it means we can't have "_" in the actual name of the id
def sanitizeLayerId(input:str):
    return input.split("_")[0]

#since we mess with underscores and layer IDs in the SVG are suffixed with weird numbers, we can't just do ==, and yes, this raise the problem of false positivie, but it's an issue for a future programmer :)
def isSvgLayerEqual(svgLayerId:str, target:str):
    if(" " in target or "_" in target):
        print("/!\\ Error: LayerPath that you want to get and modify cannot contain a \" \" or a \"_\"")
    treatedId=sanitizeLayerId(svgLayerId)
    #If the start of the layer id is the target id, then yes, it's the layer we're looking for (or a lookalike)
    return treatedId==target

def create_svg_card(cardDatas, cohort, spe, fileName, cardImagesName, isPreview=False):
    svgTemplatePath=os.path.join(os.getcwd(),settings["TemplateSvgFile"])
    tree = ET.parse(svgTemplatePath)

    root = tree.getroot()

    cardNameLayer = get_svg_layer_by_path(root,settings["CardNameLayer"])
    change_text_of_svg_layer(cardNameLayer,cardDatas["card_name"])
    print(cardDatas["card_name"])

    ownerNameLayer = get_svg_layer_by_path(root,settings["OwnerNameLayer"])
    change_text_of_svg_layer(ownerNameLayer,cardDatas["owner_name"])

    output = BytesIO()
    tree.write(output, encoding='utf-8', xml_declaration=True) 
    print(output.getvalue())  # your XML file, encoded as UTF-8
    with open("output.svg", "wb") as f:
        f.write(output.getbuffer())


def fill_layers_for_skill(ps, skillLayerGroup, skillDatas):
    skillDescLayer=skillLayerGroup.artLayers.getByName(settings["SkillDescLayerName"])
    skillDescLayer.textItem.contents=replacePingsByCardNames(skillDatas["skill_desc"])
    skillTitleLayer=skillLayerGroup.artLayers.getByName(settings["SkillTitleLayerName"])
    skillTitleLayer.textItem.contents=replacePingsByCardNames(skillDatas["skill_name"])
    skillCostLayer=skillLayerGroup.artLayers.getByName(settings["SkillCostLayerName"])
    skillCostLayer.textItem.contents=str(skillDatas["skill_cost"])

    spe1IconGroup=skillLayerGroup.layerSets.getByName(settings["Spe1IconGroupName"])
    set_spe_image(spe1IconGroup,skillDatas["spe1"],"IconLayerName")

    spe2IconGroup=skillLayerGroup.layerSets.getByName(settings["Spe2IconGroupName"])
    set_spe_image(spe2IconGroup,skillDatas["spe2"],"IconLayerName")

    spe3IconGroup=skillLayerGroup.layerSets.getByName(settings["Spe3IconGroupName"])
    set_spe_image(spe3IconGroup,skillDatas["spe3"],"IconLayerName")

    return

def set_spe_image(speIconsGroup, speId, imageLayerKey):
    chosenSpe=None
    for spe in settings["Specialties"]:
        if spe["Id"]==speId:
            chosenSpe=spe
            break
    
    if(chosenSpe==None):
        speIconsGroup.visible=False
        return

    for iconLayer in speIconsGroup.artLayers:
        iconLayer.visible=iconLayer.name==chosenSpe[imageLayerKey]
#endregion

#region Bot management
specialtiesChoices=[]

for spe in settings["Specialties"]:
    specialtiesChoices.append(app_commands.Choice(name=spe["DisplayName"], value=spe["Id"]))

def replacePingsByCardNames(startString:str):
    matches=re.finditer("\<@([^\>\[]*)>",startString)
    for matchObject in matches:
        userId=matchObject.group().replace("<@","").replace(">","")
        user=get_user(userId)
        cardName="\"[CARD_NOT_FOUND]\""
        if(user!=None):
            cardName=get_or_create_card(user,True)["card_name"]
        startString=startString.replace(matchObject.group(),"\""+cardName+"\"")
    return startString

@tree.command(
    name="help",
    description="Get help with how to create Pokenjmin's cards using Mecha Buendia"
)
async def help(interaction):
    await interaction.response.send_message(settings["HelpMessage"],ephemeral=True)
    if(interaction.user.id in settings["Admins"]):
        await interaction.followup.send(settings["AdminHelpMessage"],ephemeral=True)

@tree.command(
    name="set_current_server_as_main",
    description="Make this server your main. It determines how your spe is computed"
)
async def setCurrentServerAsMain(interaction):
    update_user_guild(interaction.user.id, interaction.guild_id)
    await interaction.response.send_message("The current server is now marked as your main !",ephemeral=True)

@tree.command(
    name="set_card",
    description="Set the value of one or more fields of your card"
)
@app_commands.describe(card_name="The name at the top of the card")
@app_commands.describe(owner_name="YOUR name, on the left side")
@app_commands.describe(hp_name="The name beside the HP's value at the top of the card")
@app_commands.describe(hp_value="HP's value at the top of the card")
async def setCard(interaction, card_name:str=None, owner_name:str=None,hp_name:str=None, card_description:str=None, bottom_text_title:str=None, 
                  bottom_text_content:str=None, hp_value:int=None, card_image:discord.Attachment=None, owner_image:discord.Attachment=None):
    user=get_or_create_user(interaction.user.id, interaction.guild_id)
    card=get_or_create_card(user)
    feedbackMessage=""
    error=False

    if hp_value!=None and hp_value>999 :
        feedbackMessage+="/!\\ HP Value is limited to 999 max !\n"
        hp_value=999
    
    if hp_value!=None and hp_value<-99 :
        feedbackMessage+="/!\\ HP Value is limited to -99 min !\n"
        hp_value=-99

    if hp_name!=None and len(hp_name)>3 : 
        feedbackMessage+="HP Name length is limited to 3 characters !\n"

    if(card_name!=None): card["card_name"]=card_name
    if(owner_name!=None): card["owner_name"]=owner_name
    if(hp_name!=None): card["cp_name"]=hp_name
    if(card_description!=None): card["card_description"]=card_description
    if(bottom_text_title!=None): card["bottom_text_title"]=bottom_text_title
    if(bottom_text_content!=None): card["bottom_text_content"]=bottom_text_content
    if(hp_value!=None): card["cp_value"]=hp_value


    fileName=get_discord_id_of_card(card)
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
                    feedbackMessage+="card_image isn't in the preferred ratio "+str(settings["CardImagesPreferredRatio"])+" it may not fit as you wish, consider modifying the image to be in the preferred ratio with dimensions of, for example "+str(1080)+"\\*"+str(math.ceil(1080*settings["CardImagesPreferredRatio"]))+"\n"
                im.save(os.path.join(os.getcwd(),settings["CardImagesFolder"],str(fileName)+".png"))
        except:
            feedbackMessage+="There was an error converting the card_image, try exporting it to another format like png or jpg\n"
            error=True

    if(owner_image!=None):
        if owner_image.content_type.split("/")[0]!="image":
            await interaction.response.send_message("Error: Card Image was not an image", ephemeral=True)
            return
        bruteImagePath=os.path.join(mkdtemp(),"cached_"+owner_image.filename)
        await owner_image.save(bruteImagePath)
        try:
            with Image.open(bruteImagePath) as im:
                ratio= im.width/im.height
                if(abs(ratio-settings["OwnerPhotoPreferredRatio"])>=0.005):
                    feedbackMessage+="owner_photo isn't in the preferred ratio "+str(settings["OwnerPhotoPreferredRatio"])+" it may not fit as you wish, consider modifying the image to be in the preferred ratio with dimensions of, for example "+str(1080)+"\\*"+str(math.ceil(1080*settings["OwnerPhotoPreferredRatio"]))+"\n"
                im.save(os.path.join(os.getcwd(),settings["OwnerPhotosFolder"],str(fileName)+".png"))
        except:
            feedbackMessage+="There was an error converting the card_image, try exporting it to another format like png or jpg\n"
            error=True

    update_card(card)

    if(error==False):
        feedbackMessage+="All field successfully setted !"

    await send_message_with_preview(interaction, feedbackMessage)

@tree.command(
    name="create_legendary",
    description="Create a legendary card"
)
async def createLegendary(interaction, card_name:str, owner_name:str):
    if(interaction.user.id not in settings["Admins"]):
        await interaction.response.send_message("Only admins can use this command !",ephemeral=True)
        return
    user=create_legendary_user()
    card=get_or_create_card(user)

    card["card_name"]=card_name
    card["owner_name"]=owner_name
    update_card(card)
    feedbackMessage="All field successfully setted !"
    await interaction.response.send_message(feedbackMessage,ephemeral=True)

@tree.command(
    name="list_legendaries",
    description="Get the list of all existing legendary cards"
)
async def listLegendaries(interaction):
    results=list_legendary_cards()
    returnMessage=""
    for result in results:
        returnMessage+="```"
        returnMessage+="Card name: "+result["card_name"]+"\t"
        returnMessage+="Owner name: "+result["owner_name"]+"\t"
        returnMessage+="ID: "+str(result["discord_id"])+"\t"
        returnMessage+="Insertion text: "+"<@"+result["discord_id"]+">"
        returnMessage+="```"
        returnMessage+="\n"
    await interaction.response.send_message(returnMessage,ephemeral=True)

@tree.command(
    name="set_skill",
    description="Set the value of one or more fields of your card"
)
@app_commands.choices(skill_nbr=[
    app_commands.Choice(name='Skill 1', value=1),
    app_commands.Choice(name='Skill 2', value=2)
])
@app_commands.choices(spe1=specialtiesChoices)
@app_commands.choices(spe2=specialtiesChoices)
@app_commands.choices(spe3=specialtiesChoices)
async def setSkill(interaction, skill_nbr:int, skill_name:str=None, skill_desc:str=None, skill_cost:int=None, spe1:int=None, spe2:int=None, spe3:int=None):
    user=get_or_create_user(interaction.user.id, interaction.guild_id)
    card=get_or_create_card(user)
    skill=get_skill_of_card(card,skill_nbr)
    feedbackMessage=""
    error=False

    if(skill_name!=None): skill["skill_name"]=skill_name
    if(skill_desc!=None): skill["skill_desc"]=skill_desc
    if(skill_cost!=None): skill["skill_cost"]=skill_cost
    if(spe1!=None): skill["spe1"]=spe1
    if(spe2!=None): skill["spe2"]=spe2
    if(spe3!=None): skill["spe3"]=spe3
    update_skill(skill)

    if(error==False):
        feedbackMessage+="All field successfully setted !"

    await send_message_with_preview(interaction, feedbackMessage)

@tree.command(
    name="set_server_settings",
    description="Set the default spe for a given server"
)
@app_commands.choices(default_spe=specialtiesChoices)
async def setServerSettings(interaction, default_spe:int, cohort:str):
    if(interaction.user.id not in settings["Admins"]):
        await interaction.response.send_message("Only admins can use this command !",ephemeral=True)
        return

    serverSettings=get_or_create_server_settings(interaction.guild_id)
    if(default_spe!=None): serverSettings["default_spe"]=default_spe
    if(cohort!=None): serverSettings["server_cohort"]=cohort
    update_server_settings(serverSettings)
    await interaction.response.send_message("Server settings successfully setted !",ephemeral=True)

@tree.command(
    name="set_role_settings",
    description="Set the default spe for a given server"
)
@app_commands.choices(spe=specialtiesChoices)
async def setRoleSettings(interaction, role:discord.Role, spe:int):
    if(interaction.user.id not in settings["Admins"]):
        await interaction.response.send_message("Only admins can use this command !",ephemeral=True)
        return

    roleSettings=get_or_create_role_settings(interaction.guild_id,role.id)
    if(spe!=None): roleSettings["spe"]=spe
    update_role_settings(roleSettings)
    await interaction.response.send_message("Role settings successfully setted !",ephemeral=True)

@tree.command(
        name="get_admins",
        description="List all the admins of the bot"
)
async def getAdmins(interaction):
    messageResponse="List of all admins:\n"
    for admin in settings["Admins"]:
        messageResponse+="\t<@"+str(admin)+">"
    await interaction.response.send_message(messageResponse, ephemeral=True)

@tree.command(
    name="switch_to_user_card",
    description="Allows you to set your current card to another user's one",
    guild=discord.Object(id=790626187944394772)
)
async def switchToUserCard(interaction, target:discord.User):
    if(interaction.user.id not in settings["Admins"]):
        await interaction.response.send_message("Only admins can use this command !",ephemeral=True)
        return
   
    get_or_create_user(target.id, interaction.guild_id)
    get_or_create_user(interaction.user.id, interaction.guild_id)

    update_user_overwrite(interaction.user.id, target.id)
    await interaction.response.send_message("You are now modifying the card of <@"+str(target.id)+">", ephemeral=True)

@tree.command(
    name="switch_to_legendary",
    description="Allows you to set your current card to another user's one"
)
async def switchToLegendary(interaction, target_id:str):
    if(interaction.user.id not in settings["Admins"]):
        await interaction.response.send_message("Only admins can use this command !",ephemeral=True)
        return

    get_or_create_user(interaction.user.id, interaction.guild_id)
    if(get_user(target_id)==None):
        await interaction.response.send_message("Target id is either not existant or invalid", ephemeral=True)
        return
    
    if(get_user(target_id)["legendary_user"]==False):
        await interaction.response.send_message("If you want to switch to another user's card, use switch_to_user_card instead", ephemeral=True)
        return

    update_user_overwrite(interaction.user.id, target_id)
    await interaction.response.send_message("You are now modifying the card of <@"+target_id+">", ephemeral=True)

@tree.command(
    name="reset_switch",
    description="Set your current card as your own"
)
async def resetSwitch(interaction):
    if(interaction.user.id not in settings["Admins"]):
        await interaction.response.send_message("Only admins can use this command !",ephemeral=True)
        return
    
    user=get_or_create_user(interaction.user.id, interaction.guild_id)
    update_user_overwrite(interaction.user.id, None)
    await interaction.response.send_message("Switch has been reset", ephemeral=True)

@tree.command(
    name="get_current_switch",
    description="Get what card you are modifying"
)
async def getCurrentSwitch(interaction):
    if(interaction.user.id not in settings["Admins"]):
        await interaction.response.send_message("Only admins can use this command !",ephemeral=True)
        return
    
    user=get_or_create_user(interaction.user.id, interaction.guild_id)
    currentOverwrite=user["overwrite_discord_id"]
    if(currentOverwrite==None):
        await interaction.response.send_message("You are currently modifying your own card", ephemeral=True)
        return 
    
    await interaction.response.send_message("You are currently modifying the card of <@"+currentOverwrite+">", ephemeral=True)

@tree.command(
    name="get",
    description="Prints all the values of your card in a text format, quicker than a full preview"
)
async def get(interaction):
    def skillToString(skillDatas):
        returnString=""
        returnString+="\tName: "+skillDatas["skill_name"]
        returnString+="\n\tCost: "+str(skillDatas["skill_cost"])
        returnString+="\n\tDesc: "+skillDatas["skill_desc"]
        return returnString
    
    user=get_or_create_user(interaction.user.id, interaction.guild_id)
    card=get_or_create_card(user)
    returnValue=""
    #In most cases, cardOwner is the user, but it may be another user if the current user is an admin who used the switch feature to modify a legendary card or the card of someone else
    cardOwner=get_owner_of_card(card)

    returnValue+="Owner name: "+card["owner_name"]
    returnValue+="\nCard name: "+card["card_name"]
    returnValue+="\nDescription: "+card["card_description"]
    returnValue+="\nHPs name: "+str(card["cp_name"]).upper()
    returnValue+="\nHPs value: "+str(card["cp_value"])

    bottomText = "["+card["bottom_text_title"]+"] "+card["bottom_text_content"]
    returnValue+="\nBottom Text: "+bottomText
    
    returnValue+="\nSkill 1:\n"+skillToString(get_skill_of_card(card,1))
    returnValue+="\nSkill 2:\n"+skillToString(get_skill_of_card(card,2))

    files_to_send:list[discord.File] = []
    ownerPhotoPath=os.path.join(os.getcwd(),settings["OwnerPhotosFolder"],cardOwner["discord_id"]+".png")
    cardImagePath=os.path.join(os.getcwd(),settings["CardImagesFolder"],cardOwner["discord_id"]+".png")

    if os.path.exists(ownerPhotoPath):
        files_to_send.append(discord.File(ownerPhotoPath))
    if os.path.exists(cardImagePath):
        files_to_send.append(discord.File(cardImagePath))

    await interaction.response.send_message(returnValue,ephemeral=True, files=files_to_send)

@tree.command(
    name="preview",
    description="Exports your card as a jpg"
)
async def preview(interaction):
    await send_message_with_preview(interaction,"")

async def send_message_with_preview(interaction, message):
    await interaction.response.defer(ephemeral=True, thinking=True)
    user=get_or_create_user(interaction.user.id, interaction.guild_id)
    card=get_or_create_card(user)
    #In most cases, cardOwner is the user, but it may be another user if the current user is an admin who used the switch feature to modify a legendary card or the card of someone else
    cardOwner=get_owner_of_card(card)

    mainGuildOfUser=user["guild_id"]
    serverSettings=get_server_settings(mainGuildOfUser)

    if(serverSettings==None):
        await interaction.followup.send("Your main server doesn't have settings, which are required to create a preview. Try making this server your main by using the set_current_server_as_main command, if its already the case, ask your local admin."
                                        ,ephemeral=True)
        return
    
    spe=settings["LegendarySpeId"]
    if cardOwner["legendary_user"]==0 :
        memberRoles=client.get_guild(mainGuildOfUser).get_member(int(get_discord_id_of_card(card))).roles
        spe=get_spe_for_user(mainGuildOfUser,memberRoles)
    
    fileName=get_discord_id_of_card(card)
    create_svg_card(card, serverSettings["server_cohort"], spe, fileName,str(fileName)+".png", True)
    # fileName=get_discord_id_of_card(card)
    # jpegPreviewPath=create_psd_card(card, serverSettings["server_cohort"], spe, fileName,str(fileName)+".png", True)
    # currentDir=os.getcwd()
    # os.chdir(os.path.dirname(jpegPreviewPath))
    # await interaction.followup.send(message,ephemeral=True,file=discord.File(jpegPreviewPath))
    # os.chdir(currentDir)

@client.event
async def on_ready():
    await tree.sync()

client.run(settings["Token"])
#endregion