import photoshopHandler
from bot import sanitizeTag, settings
import os
import xml.etree.ElementTree as ET

svgTemplatePath=os.path.join(os.getcwd(),settings["TemplateSvgFile"])
tree = ET.parse(svgTemplatePath)
settingsFile= open('settings.json', encoding="utf-8")
settings=json.load(settingsFile)

root = tree.getroot()

#We'll recursively find all text layers
def scanAllTextLayers(parent):
    for child in parent:
        if(sanitizeTag(child)=="text"):
            print("Text layer: "+child.tag)
        else:
            scanAllTextLayers(child)

scanAllTextLayers(root)