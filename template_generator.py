#This python script takes the Template psd and generates a folder filled with every layer as a png and a generated json file explaining to the bot.py how to construct a card using those layers.
#The point is that you run this script on a Windows computer with photoshop and everything, and then you can paste the directory on a docker implementation or any kind of linux server
#because managing psd in a python program is a nightmare, it takes a lot of time and of computing power.
from photoshop import Session
import photoshop.api as photoshop
import os
import json
from PIL import Image

settingsFile= open('settings.json', encoding="utf-8")
settings=json.load(settingsFile)

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

with Session(os.path.join(os.getcwd(),settings["TemplatePsdFile"]), action="open", auto_close=True) as ps:
    layerSets=[]
    for layerSet in ps.active_document.layerSets :
        layerSets.append(layerSet)
    for layer in ps.active_document.layers:
        print(layer.name)
        print("\t"+layer.typename)
    
    print("--------------")
    for layerSet in ps.active_document.layerSets:
        print(layerSet.name)
        print("\t"+layerSet.typename)

       