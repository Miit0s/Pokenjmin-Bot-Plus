import os
import xml.etree.ElementTree as ET
import json
from photoshop import Session
import photoshop.api as photoshop

settingsFile= open('settings.json', encoding="utf-8")
settings=json.load(settingsFile)

svgTemplatePath=os.path.join(os.getcwd(),settings["TemplateSvgFile"])
tree = ET.parse(svgTemplatePath)

root = tree.getroot()

#region Functions pasted from bot.py, yes, code duplication is bad, but it's a Python application
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

#Remove everything after a "_" in a layer id, keeping only the good part. But yes, it means we can't have "_" in the actual name of the id
def sanitizeLayerId(input:str):
    return input.split("_")[0]

#The tags are all prefixed by "{http://www.w3.org/2000/svg}", this function removes it
def sanitizeTag(input:str):
    return input.replace("{http://www.w3.org/2000/svg}","")
#endregion

#We'll recursively find all text layers
def scanAllTextLayers(ps,parent, pathToParent):
    for child in parent:
        tag=sanitizeTag(child.tag)
        if(tag!="g"): continue
        if("id" not in child.attrib): continue

        id=sanitizeLayerId(child.attrib["id"])

        pathToSelf=pathToParent
        if pathToParent!="": pathToSelf+="/"
        #To get the path we use data name when available, more reliable and always the same as in photoshop
        if("data-name" in child.attrib):
            pathToSelf+=sanitizeLayerId(child.attrib["data-name"])
        else:
            pathToSelf+=id

        textComp=None
        for comp in child:
            if(sanitizeTag(comp.tag)=="text"):
                textComp=comp
                break
        
        scanAllTextLayers(ps,child,pathToSelf)
        if(textComp==None):
            continue

        print("Text Layer: "+pathToSelf)
        print("Locating photoshop version")
        photoshopLayer=get_layer_by_path(ps,pathToSelf)
        print(photoshopLayer.textItem.contents)

with Session(os.path.join(os.getcwd(),settings["TemplatePsdFile"]), action="open", auto_close=True) as ps:
    scanAllTextLayers(ps,root,"")