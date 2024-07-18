#This python script takes the Template psd and generates a folder filled with every layer as a png and a generated json file explaining to the bot.py how to construct a card using those layers.
#The point is that you run this script on a Windows computer with photoshop and everything, and then you can paste the directory on a docker implementation or any kind of linux server
#because managing psd in a python program is a nightmare, it takes a lot of time and of computing power.
from photoshop import Session
import photoshop.api as photoshop
import os
import json
from PIL import Image
from collections import OrderedDict
import pdf2image
from tempfile import mkdtemp

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

#Don't work if 2 layer in the parent layer set have the same name
def isLayerALayerSet(targetLayer, parentLayerSet):
    for subLayerSet in parentLayerSet.layerSets:
        if subLayerSet.name==targetLayer.name: return True
    return False

def justificationToString(justification):
    if justification==photoshop.Justification.FullyJustified : return "FullyJustified"
    if justification==photoshop.Justification.Center : return "Center"
    if justification==photoshop.Justification.CenterJustified : return "CenterJustified"
    if justification==photoshop.Justification.Left : return "Left"
    if justification==photoshop.Justification.LeftJustified : return "LeftJustified"
    if justification==photoshop.Justification.Right : return "Right"
    if justification==photoshop.Justification.RightJustified : return "RightJustified"

    #if the justification is weird (a conjugate) we'll assume the text isn't to be replaced and export the layer as an image
    return "Image"

def exportLayerAsPng(ps, layerPath, exportPath):
    #make all layers non visible
    for layer in ps.active_document.layers:
        layer.visible=False

    #split the path into multiple part
    subGroups=str(layerPath).split("/")
    #if the path is not nested, it's easy, we just set the layer we want as visible
    if(len(subGroups)<=1):
        ps.active_document.artLayers.getByName(layerPath).visible=True
    #but if not, we have to recursively make it visible while keeping the neighbors not visible
    else:
        i=0
        layerGroup=ps.active_document
        while(i<len(subGroups)-1):
            for layer in layerGroup.layers :
                layer.visible=False
            layerGroup= layerGroup.layerSets.getByName(subGroups[i])
            layerGroup.visible=True
            i+=1

        for artLayer in layerGroup.artLayers:
            artLayer.visible=False
            
        layerGroup.artLayers.getByName(subGroups[len(subGroups)-1]).visible=True

    #Now we can just export it :)
    if not os.path.exists(os.path.dirname(exportPath)):
        os.makedirs(os.path.dirname(exportPath))

    options=ps.ExportOptionsSaveForWeb()
    #if you're reading this code to understand how to export as png, don't forget the "options.PNG8=True" that isn't mentionned anywhere in the doc or on the internet
    options.PNG8=True
    ps.active_document.exportDocument(os.path.join(os.getcwd(),exportPath), ps.ExportType.SaveForWeb, options)

with Session(os.path.join(os.getcwd(),settings["TemplatePsdFile"]), action="open", auto_close=True) as ps:
    #We recursively turn the layer sets and their sublayerS/sublayerSets into dict object
    #a layer set is a layer group, an artlayer a regular layer. We can't use layer.typename because it doesn't work (always return "artLayer" even for layerSets)
    def layerSetToDict(layerSet, namePrintPrefix, parentLayerPath):
        layerSetAsDict={}
        for layer in layerSet.layers:
            newChild={}
            newChildName=layer.name
            selfLayerPath=str(parentLayerPath+layer.name)

            newChild["bounds"]=layer.bounds
            newChild["visible"]=layer.visible
            newChild["opacity"]=layer.opacity
            print(namePrintPrefix+layer.name+" "+selfLayerPath)

            if isLayerALayerSet(layer, layerSet):
                newChild["type"]="layerSet"
                newChild["layers"]=layerSetToDict(layer,namePrintPrefix+"\t",selfLayerPath+"/")
                layerSetAsDict[newChildName]=newChild
                continue

            #For an unknown reason even "hasattr" make the software crash if layer has no textItem, so we added a try block just for it, because there's no way to check if textItem is assigned without making the software crash is the answer is no
            try:       
                if layer.textItem!=None:
                    try:
                        justif=justificationToString(layer.textItem.justification)
                    except:
                        print("/!\ Couldn't get the justification for "+layer.name+"Gonna assume it's left aligned")
                        justif=photoshop.Justification.Left

                    if(justif!="Image" and selfLayerPath not in settings["TextLayerToPreRender"]):
                        newChild["type"]="textLayer"
                        newChild["textContent"]=layer.textItem.contents
                        newChild["font"]=layer.textItem.font
                        newChild["color"]=layer.textItem.color.rgb.hexValue
                        newChild["justification"]=justif
                        layerSetAsDict[newChildName]=newChild
                        continue
                    #print("-----------------NOT TEXT --------------------- BECAUSE"+justif+" "+str(layer.textItem.justification))
            except:
                pass

            newChild["type"]="Image"

            #Now let's export the layer as an image, we add every path to a list of psd to then convert them in PNG as a batch (couldn't get each layer to export nicely as a png one by one)
            localPath=os.path.join(settings["GeneratedLayersFolder"],selfLayerPath)
            absolutePath=os.path.join(os.getcwd(),localPath)

            exportLayerAsPng(ps,selfLayerPath,absolutePath+".png")

            newChild["ImagePath"]=localPath+".png"
            layerSetAsDict[newChildName]=newChild

        #In photoshop, the first layer is on the top, but with programmer logic it's the opposite, so we flip all dictionnaries
        return dict(reversed(list(layerSetAsDict.items())))  

    with open(settings["GeneratedTemplateJson"], 'w') as fp:
        json.dump(layerSetToDict(ps.active_document,"",""), fp)
    
    print("Done !")
