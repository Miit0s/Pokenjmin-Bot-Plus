import discord
import json
from discord import app_commands
import sqlite3
import os
from tempfile import mkdtemp
from PIL import Image
import subprocess
from reportlab.graphics import renderPDF, renderPM
import re
import xml.etree.ElementTree as ET
import math
from io import BytesIO
import threading
import asyncio

os.environ['PYTHONUNBUFFERED'] = "1"


#Only windows computer supports the photoshop api
photoshopSupported=True
try:
    from photoshop import Session
    import photoshop.api as photoshop
except:
    photoshopSupported=False


intents = discord.Intents.default()
intents.members=True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
settingsFile= open('settings.json', encoding="utf-8")

print("Settings:")
with open('settings.json', 'r') as fin:
    print(fin.read())


settings=json.load(settingsFile)
con = sqlite3.connect("Data/data.db")
con.row_factory = sqlite3.Row

#Node namespace, to add at the start of any node we create
nodeNamespace="ns0:"
#Same with atrib
attribNamespace="ns1:"

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

if photoshopSupported:
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

#Get layer by path written as Group/Group/Layer, for exampel Infos/Name
def get_svg_layer_by_path(root, layerPath):
    subGroups=str(layerPath).split("/")
    currentLayer=root
    if(" " in layerPath or "_" in layerPath):
        print("/!\\ Error: layerPath:"+layerPath+" contains a forbidden character: \" \" or a \"_\"")

    for group in subGroups:
        nextLayer=None
        for child in currentLayer:
            if sanitizeTag(child.tag)!="g":continue
            #If the g node has no id, it's probably a mask, so we just replace it with its "true" layer child
            if('id' not in child.attrib): 
                gChild=child[0]
                if(gChild==None): continue
                if(sanitizeTag(gChild.tag)!="g"):continue
                if('id' not in gChild.attrib):continue
                child=gChild
            #If there's a child data-name we can try it too for more accuracy
            if isSvgLayerEqual(child.attrib['id'],group) or ("data-name" in child.attrib and child.attrib["data-name"]==group):
                nextLayer=child
                break
        if(nextLayer==None):
            print("/!\\Couldn't find the layer "+layerPath)
        currentLayer=nextLayer
    return currentLayer

def split_string_to_wrap_text(text:str, maxCharacters:int):
    words=text.split(" ")
    lines=[]
    currentLine=""
    while len(words)>0:
        if(len(currentLine)+len(words[0])>maxCharacters):
            #if current word is longer than a line, we need to cut it and fit it anyway
            if(len(words[0])>maxCharacters):
                freeSpaceOnCurrentLine=(maxCharacters-len(currentLine))
                keptPart=words[0][0:freeSpaceOnCurrentLine]
                words[0]=words[0][freeSpaceOnCurrentLine:len(words[0])]
                currentLine+=" "+keptPart
            lines.append(currentLine)
            currentLine=""
            continue
        currentLine+=" "+words[0]
        words.remove(words[0])
    lines.append(currentLine)
    return lines 

def getFontSizeFromStyle(style:str):
    pattern = r"font-size:\s*([\d.]+)px"
    match = re.search(pattern, style)
    fontSize=float(match.group(1))
    return fontSize

#Allow us to find the real biggest tspan even taking into account nesting
def getTspanMaxLength(tspan, maxLengthSoFar):
    if(tspan.text!=None and len(tspan.text)>maxLengthSoFar):
        maxLengthSoFar=len(tspan.text)
    for child in tspan:
        if(sanitizeTag(child.tag)!="tspan"): continue
        maxLengthSoFar=getTspanMaxLength(child, maxLengthSoFar)
    return maxLengthSoFar

def change_text_of_svg_layer(layer,text:str):
    text=str(text)
    textDiv=None
    for child in layer:
        if sanitizeTag(child.tag)=="text":
            textDiv=child
            break
    if(textDiv==None):
        print("/!\\Couldn't find a text layer for  "+layer.attrib['id'])

    #Now we check if textDiv contains tspans
    hasTSpan=False
    caracPerLine=0
    for textDivChild in textDiv:
        if sanitizeTag(textDivChild.tag)!="tspan":
            continue
        hasTSpan=True
        if(textDivChild.text==None): 
            continue
        caracPerLine=max(caracPerLine,len(textDivChild.text))
    #No tspan: We got a easy case here, the field is on a single line, our job is done, yay !
    if(hasTSpan==False):
        textDiv.text=text
        return
    caracPerLine=getTspanMaxLength(textDiv, caracPerLine)
    #So, we have tspans, that means we are face to face with a multiline text, but we now how much caractere fits in a line, se we can use this
    attributes=textDiv.attrib
    textDiv.clear()
    textDiv.attrib=attributes

    lines=split_string_to_wrap_text(text, caracPerLine)
    textDiv.text=lines[0]
    lines.remove(lines[0])
    i=0
    while len(lines)>0:
        i+=1
        tspan=ET.SubElement(textDiv,nodeNamespace+"tspan")
        tspan.attrib={"x":"0", "y":str(i*math.floor(getFontSizeFromStyle(textDiv.attrib["style"]))) }
        tspan.text=lines[0]
        lines.remove(lines[0])

def toggle_svg_layer_visibility(layer, visibility:bool):
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
        return
    
    layer.attrib["style"]=desiredString+layer.attrib["style"]


#node.find doesn't work because the tags are prefixed with bullshit, so we made our own version
def find_child_by_sanitize_tag(node, tag):
    for child in node:
        if(sanitizeTag(child.tag)==tag):
            return child
    return None

def translate_node(node, deltaX,deltaY, relativeToScale:bool=True):
    #First we get and store the transform attribute
    transform=node.attrib["transform"]
    # Extraire les valeurs de translation
    translatePattern = r'translate\(([^)]+)\)'
    translateMatch = re.search(translatePattern, transform)

    scale_pattern = r'scale\(([^)]+)\)'
    scale_match = re.search(scale_pattern, transform)
    scaleFactor=1
    if scale_match and relativeToScale:
        #sometime the scale is sliglty different on x and y, leading to 2 value, but we can afford to not care
        scaleFactor = float(scale_match.group(1).split(" ")[0])
    
    values = translateMatch.group(1).split(" ")
    x = float(values[0])
    y = float(values[1]) if len(values) > 1 else 0.0
    x += scaleFactor*deltaX
    y += scaleFactor*deltaY

    newTransformString=transform.replace(f"translate({translateMatch.group(1)})",f"translate({x} {y})")
    node.attrib["transform"]=newTransformString

def replace_image_for_svg(root,layerToReplacePath, input_file):
    layer=get_svg_layer_by_path(root,layerToReplacePath)
    imageNode=find_child_by_sanitize_tag(layer,"image")
    svgFolder=os.path.join(os.getcwd(),settings["GeneratedSvgsFolder"])
    imageRelativePath=os.path.relpath(input_file,svgFolder)
    imageNode.attrib[attribNamespace+"href"]=imageRelativePath

    #we get the ratio of the new image using PILImage
    newImageFile = Image.open(input_file)
    width, height = newImageFile.size
    ratio = float(width) / float(height)

    referenceWidth=float(imageNode.attrib["width"])
    referenceHeight=float(imageNode.attrib["height"])
    referenceRatio=referenceWidth/referenceHeight
    newReferenceWidth=referenceWidth
    newReferenceHeight=referenceHeight

    #if we're wider than the reference ratio, width is dictated by height
    if(ratio>referenceRatio):
        print("biggerRatio")
        newReferenceWidth=ratio*referenceHeight
    else:
        print("smallerRatio")
        print(ratio)
        newReferenceHeight=referenceWidth/ratio
    
    widthDiff=newReferenceWidth-referenceWidth
    heightDiff=newReferenceHeight-referenceHeight
    translate_node(imageNode,-widthDiff/2,-heightDiff/2)

    imageNode.attrib["width"]=str(math.ceil(newReferenceWidth))
    imageNode.attrib["height"]=str(math.ceil(newReferenceHeight))

    
#The tags are all prefixed by "{http://www.w3.org/2000/svg}", this function removes it
def sanitizeTag(input:str):
    return input.replace("{http://www.w3.org/2000/svg}","")

#Remove everything after a "_" in a layer id, keeping only the good part. But yes, it means we can't have "_" in the actual name of the id
def sanitizeLayerId(input:str):
    return input.split("_")[0]

#since we mess with underscores and layer IDs in the SVG are suffixed with weird numbers, we can't just do ==, and yes, this raise the problem of false positivie, but it's an issue for a future programmer :)
def isSvgLayerEqual(svgLayerId:str, target:str):
    if(" " in target or "_" in target):
        print("/!\\ Error: layerPath:"+target+" contains a forbidden character: \" \" or a \"_\"")
    treatedId=sanitizeLayerId(svgLayerId)
    #If the start of the layer id is the target id, then yes, it's the layer we're looking for (or a lookalike)
    return treatedId==target

def create_svg_card(cardDatas, cohort, spe, fileName, cardImagesName, isPreview=False):   
    svgTemplatePath=os.path.join(os.getcwd(),settings["TemplateSvgFile"])
    tree = ET.parse(svgTemplatePath)

    root = tree.getroot()

    previewWatermark=get_svg_layer_by_path(root,settings["PreviewLayerGroup"])
    toggle_svg_layer_visibility(previewWatermark,isPreview)
    
    cardNameLayer = get_svg_layer_by_path(root,settings["CardNameLayer"])
    change_text_of_svg_layer(cardNameLayer,cardDatas["card_name"])
    print(cardDatas["card_name"])

    ownerNameLayer = get_svg_layer_by_path(root,settings["OwnerNameLayer"])
    change_text_of_svg_layer(ownerNameLayer,cardDatas["owner_name"])

    descriptionLayer = get_svg_layer_by_path(root,settings["DescriptionLayer"])
    change_text_of_svg_layer(descriptionLayer, replacePingsByCardNames(cardDatas["card_description"]))

    cpNameLayer = get_svg_layer_by_path(root,settings["CPNameLayer"])
    change_text_of_svg_layer(cpNameLayer, str(cardDatas["cp_name"]).upper())

    cpValueLayer = get_svg_layer_by_path(root,settings["CPValueLayer"])
    change_text_of_svg_layer(cpValueLayer, str(cardDatas["cp_value"]))

    bottomTextLayer = get_svg_layer_by_path(root,settings["BottomTextLayer"])
    change_text_of_svg_layer(bottomTextLayer, "["+cardDatas["bottom_text_title"]+"] "+replacePingsByCardNames(cardDatas["bottom_text_content"]))

    skill1Datas=get_skill_of_card(cardDatas,1)
    skill1LayerPath=settings["Skill1Group"]
    fill_layers_for_skill(root,skill1LayerPath,skill1Datas)

    skill2Datas=get_skill_of_card(cardDatas,2)
    skill2LayerPath=settings["Skill2Group"]
    fill_layers_for_skill(root, skill2LayerPath,skill2Datas)

    cardImagePath=os.path.join(os.getcwd(),settings["CardImagesFolder"],cardImagesName)
    if os.path.exists(cardImagePath):
        replace_image_for_svg(root,settings["CardImageLayer"],cardImagePath)

    ownerPhotoPath=os.path.join(os.getcwd(),settings["OwnerPhotosFolder"],cardImagesName)
    if os.path.exists(ownerPhotoPath):
        replace_image_for_svg(root,settings["OwnerPhotoLayer"],ownerPhotoPath)
    
    if(spe==None): spe=0

    speIconLayerGroup=get_svg_layer_by_path(root,settings["SpeIconGroupName"])
    set_spe_image_for_svg(speIconLayerGroup,spe,"IconLayerName")

    backgroundLayerGroup=get_svg_layer_by_path(root,settings["BackgroundsGroupName"])
    set_spe_image_for_svg(backgroundLayerGroup, spe,"BackgroundLayerName")

    cohortNameLayer = get_svg_layer_by_path(root,settings["CohortNameValueLayer"])
    change_text_of_svg_layer(cohortNameLayer,cohort)

    output = BytesIO()
    tree.write(output, encoding='utf-8', xml_declaration=True) 
    generatedSvgPath=os.path.join(os.getcwd(),settings["GeneratedSvgsFolder"],fileName+settings["GeneratedSvgsExtension"])
    with open(generatedSvgPath, "wb") as f:
        f.write(output.getbuffer())
    
    #now that we have the svg, we must convert it to jpeg
    pngPath = os.path.join(mkdtemp(),str(fileName)+".png")
    #inkScape is the only software that respects our svg, so we'll just run it
    inkscapeCommand="inkscape "+os.path.relpath(generatedSvgPath, os.getcwd())+" --export-filename="+os.path.relpath(pngPath, os.getcwd())+" --export-dpi="+str(settings["PreviewDPI"])
    os.system(inkscapeCommand)
    return pngPath


def fill_layers_for_skill(root,skillLayerGroupPath,skillDatas):
    print(skillLayerGroupPath+"/"+settings["SkillDescLayerName"])
    skillDescLayer=get_svg_layer_by_path(root, skillLayerGroupPath+"/"+settings["SkillDescLayerName"])
    change_text_of_svg_layer(skillDescLayer,replacePingsByCardNames(skillDatas["skill_desc"]))

    skillTitleLayer=get_svg_layer_by_path(root, skillLayerGroupPath+"/"+settings["SkillTitleLayerName"])
    change_text_of_svg_layer(skillTitleLayer,skillDatas["skill_name"])

    skillCostLayer=get_svg_layer_by_path(root, skillLayerGroupPath+"/"+settings["SkillCostLayerName"])
    change_text_of_svg_layer(skillCostLayer,skillDatas["skill_cost"])

    spe1IconGroup= get_svg_layer_by_path(root, skillLayerGroupPath+"/"+settings["Spe1IconGroupName"])
    set_spe_image_for_svg(spe1IconGroup,skillDatas["spe1"],"IconLayerName")

    spe2IconGroup=get_svg_layer_by_path(root, skillLayerGroupPath+"/"+settings["Spe2IconGroupName"])
    set_spe_image_for_svg(spe2IconGroup,skillDatas["spe2"],"IconLayerName")

    spe3IconGroup=get_svg_layer_by_path(root, skillLayerGroupPath+"/"+settings["Spe3IconGroupName"])
    set_spe_image_for_svg(spe3IconGroup,skillDatas["spe3"],"IconLayerName")

    return

def set_spe_image_for_svg(speIconsGroup, speId, imageLayerKey):
    chosenSpe=None
    for spe in settings["Specialties"]:
        if spe["Id"]==speId:
            chosenSpe=spe
            break
    
    if(chosenSpe==None):
        toggle_svg_layer_visibility(speIconsGroup,False)
        return

    for iconLayer in speIconsGroup:
        if sanitizeTag(iconLayer.tag) != "g":continue
        toggle_svg_layer_visibility(iconLayer, sanitizeLayerId(iconLayer.attrib["id"])==chosenSpe[imageLayerKey])
#endregion

#region Bot management
specialtiesChoices=[]

for spe in settings["Specialties"]:
    specialtiesChoices.append(app_commands.Choice(name=spe["DisplayName"], value=spe["Id"]))

def replacePingsByCardNames(startString:str):
    matches=re.finditer("\\<@([^\>\[]*)>",startString)
    for matchObject in matches:
        userId=matchObject.group().replace("<@","").replace(">","")
        user=get_user(userId)
        cardName="\"[CARD_NOT_FOUND]\""
        if(user!=None):
            cardName=get_or_create_card(user,True)["card_name"]
        startString=startString.replace(matchObject.group(),"\""+cardName+"\"")
    return startString

#returns in a percentage how much the person have progressed on their card
def getProgressionForUser(userid:str):
    totalFields=0
    filledFields=0

    def isFilled(field:str):
        return field!=None and field!=""

    def countSkill(skillDatas, totalFields, filledFields):
        #the others fields have a default value so they're not counted, and nobody is filling just one part of their skill, so it's ok
        totalFields+=1
        if(isFilled(skillDatas["skill_desc"])): filledFields+=1
        return totalFields, filledFields

    user=get_user(userid)
    if(user==None): return 0

    card=get_or_create_card(user)

    totalFields+=5
    if(isFilled(card["owner_name"])): filledFields+=1
    if(isFilled(card["card_name"])): filledFields+=1
    if(isFilled(card["card_description"])): filledFields+=1
    if(isFilled(card["cp_name"])): filledFields+=1
    if(isFilled(card["bottom_text_content"])): filledFields+=1

    totalFields,filledFields=countSkill(get_skill_of_card(card,1),totalFields,filledFields)
    totalFields,filledFields=countSkill(get_skill_of_card(card,2),totalFields,filledFields)

    totalFields+=2
    ownerPhotoPath=os.path.join(os.getcwd(),settings["OwnerPhotosFolder"],userid+".png")
    cardImagePath=os.path.join(os.getcwd(),settings["CardImagesFolder"],userid+".png")
    if os.path.exists(ownerPhotoPath):
        filledFields+=1
    if os.path.exists(cardImagePath):
        filledFields+=1
    
    #print(f"filledFields: {filledFields}, totalFields:{totalFields}")
    return float(filledFields)/float(totalFields)

@tree.command(
    name="help",
    description="Get help with how to create Pokenjmin's cards using Mecha Buendia"
)
async def help(interaction):
    await interaction.response.send_message(settings["HelpMessage"],ephemeral=True)
    if(str(interaction.user.id) in settings["Admins"]):
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
            await interaction.response.send_message("Error: Owner Image was not an image", ephemeral=True)
            return
        bruteOwnerImagePath=os.path.join(mkdtemp(),"cached_"+owner_image.filename)
        await owner_image.save(bruteOwnerImagePath)
        try:
            with Image.open(bruteOwnerImagePath) as im:
                ratio= im.width/im.height
                if(abs(ratio-settings["OwnerPhotoPreferredRatio"])>=0.005):
                    feedbackMessage+="owner_photo isn't in the preferred ratio "+str(settings["OwnerPhotoPreferredRatio"])+" it may not fit as you wish, consider modifying the image to be in the preferred ratio with dimensions of, for example "+str(1080)+"\\*"+str(math.ceil(1080*settings["OwnerPhotoPreferredRatio"]))+"\n"
                im.save(os.path.join(os.getcwd(),settings["OwnerPhotosFolder"],str(fileName)+".png"))
        except:
            feedbackMessage+="There was an error converting the owner image, try exporting it to another format like png or jpg\n"
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
    if(str(interaction.user.id) not in settings["Admins"]):
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
    
    if returnMessage=="":
        returnMessage+="There are currently no legendaries"
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
    if(str(interaction.user.id) not in settings["Admins"]):
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
    if(str(interaction.user.id) not in settings["Admins"]):
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
    if(str(interaction.user.id) not in settings["Admins"]):
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
    if(str(interaction.user.id) not in settings["Admins"]):
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
    if(str(interaction.user.id) not in settings["Admins"]):
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
    if(str(interaction.user.id) not in settings["Admins"]):
        await interaction.response.send_message("Only admins can use this command !",ephemeral=True)
        return
    
    user=get_or_create_user(interaction.user.id, interaction.guild_id)
    currentOverwrite=user["overwrite_discord_id"]
    if(currentOverwrite==None):
        await interaction.response.send_message("You are currently modifying your own card", ephemeral=True)
        return 
    
    await interaction.response.send_message("You are currently modifying the card of <@"+currentOverwrite+">", ephemeral=True)

@tree.command(
    name="get_advancement",
    description="Prints the advancement of all the people of a role in your server, who did their card and who didn't",
    #guild=discord.Object(id=790626187944394772)
)
@app_commands.describe(enumerate_empty="List the names of those who have a currently empty card")
@app_commands.describe(enumerate_partial="List the names of those who have a currently partially filled card")
@app_commands.describe(enumerate_complete="List the names of those who have a completely filled card")
async def getAdvancement(interaction, role:discord.Role, enumerate_empty:bool=True, enumerate_partial:bool=True, enumerate_complete:bool=False):
    if(str(interaction.user.id) not in settings["Admins"]):
        await interaction.response.send_message("Only admins can use this command !",ephemeral=True)
        return
    
    emptyUsers=[]
    partialUsers=[]
    completeUsers=[]
    #We iterate over all the members of the discord but ignore all who don't have the role
    for member in interaction.guild.members:
        if(role not in member.roles): continue
        progression:float=getProgressionForUser(str(member.id))

        if(progression==0):
            emptyUsers.append(member.id)
            continue

        if(progression==1):
            completeUsers.append(member.id)
            continue
        
        partialUsers.append({
            "id":member.id,
            "progression":progression
        })
    
    returnString=""
    totalCount=len(emptyUsers)+len(partialUsers)+len(completeUsers)
    returnString+=f"Empty: {len(emptyUsers)}/{totalCount}\n"
    if(enumerate_empty):
        for emptyUser in emptyUsers:
            returnString+=f"\t<@{emptyUser}>\n"
    returnString+=f"Partial: {len(partialUsers)}/{totalCount}\n"
    if(enumerate_partial):
        for partialUser in partialUsers:
            returnString+="\t<@"+partialUser["id"]+"}>: "+str(100*partialUser["progression"])+"%\n"
    returnString+=f"Complete: {len(completeUsers)}/{totalCount}\n"
    if(enumerate_empty):
        for completeUser in completeUsers:
            returnString+=f"\t<@{completeUser}>\n"

    await interaction.response.send_message(returnString,ephemeral=True)

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
    cohort=settings["LegendaryCohort"]
    if cardOwner["legendary_user"]==0 :
        memberRoles=client.get_guild(mainGuildOfUser).get_member(int(get_discord_id_of_card(card))).roles
        spe=get_spe_for_user(mainGuildOfUser,memberRoles)
        cohort=serverSettings["server_cohort"]
    
    fileName=get_discord_id_of_card(card)
    jpegPreviewPath=create_svg_card(card,  cohort, spe, fileName,str(fileName)+".png", True)
    currentDir=os.getcwd()
    os.chdir(os.path.dirname(jpegPreviewPath))
    await interaction.followup.send(message,ephemeral=True,file=discord.File(jpegPreviewPath))
    os.chdir(currentDir)

@client.event
async def on_ready():
    await tree.sync()
    await tree.sync(guild=discord.Object(id=790626187944394772))

print("esfijerighzegriuhzergiuhzegroihzerogiheroigjhsdfoijsdfgoivheroigherigheorighsdoifghseofigh")
client.run(settings["Token"])
#endregion