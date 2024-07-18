
from photoshop import Session
import photoshop.api as photoshop
import discord
import json
from discord import app_commands
import sqlite3
import os
from tempfile import mkdtemp
from PIL import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF, renderPM
import re
import xml.etree.ElementTree as ET
import math
from io import BytesIO
import bot

settingsFile= open('settings.json', encoding="utf-8")
settings=json.load(settingsFile)

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
        descriptionLayer.textItem.contents = bot.replacePingsByCardNames(cardDatas["card_description"])

        cpNameLayer = get_layer_by_path(ps,settings["CPNameLayer"])
        cpNameLayer.textItem.contents = str(cardDatas["cp_name"]).upper()

        cpValueLayer = get_layer_by_path(ps,settings["CPValueLayer"])
        cpValueLayer.textItem.contents = str(cardDatas["cp_value"])

        bottomTextLayer = get_layer_by_path(ps,settings["BottomTextLayer"])
        bottomTextLayer.textItem.contents = "["+cardDatas["bottom_text_title"]+"] "+bot.replacePingsByCardNames(cardDatas["bottom_text_content"])

        cardImagePath=os.path.join(os.getcwd(),settings["CardImagesFolder"],cardImagesName)
        if os.path.exists(cardImagePath):
            cardImageLayer=get_layer_by_path(ps,settings["CardImageLayer"])
            replace_image(ps,cardImageLayer,cardImagePath)

        ownerPhotoPath=os.path.join(os.getcwd(),settings["OwnerPhotosFolder"],cardImagesName)
        if os.path.exists(ownerPhotoPath):
            ownerPhotoLayer=get_layer_by_path(ps,settings["OwnerPhotoLayer"])
            replace_image(ps,ownerPhotoLayer,ownerPhotoPath)

        skill1Datas=bot.get_skill_of_card(cardDatas,1)
        skill1LayerSet=ps.active_document.layerSets.getByName(settings["Skill1Group"])
        fill_layers_for_skill(ps,skill1LayerSet,skill1Datas)

        skill2Datas=bot.get_skill_of_card(cardDatas,2)
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
    skillDescLayer.textItem.contents=bot.replacePingsByCardNames(skillDatas["skill_desc"])
    skillTitleLayer=skillLayerGroup.artLayers.getByName(settings["SkillTitleLayerName"])
    skillTitleLayer.textItem.contents=bot.replacePingsByCardNames(skillDatas["skill_name"])
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
