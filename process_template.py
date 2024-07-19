#Make treatments to the svg template using datas from the photoshop to make it closer to its psd counterpart
import os
import xml.etree.ElementTree as ET
import json
from photoshop import Session
import photoshop.api as photoshop
from io import BytesIO
import re
import math

settingsFile= open('settings.json', encoding="utf-8")
settings=json.load(settingsFile)

unprocessedSvgTemplatePath=os.path.join(os.getcwd(),settings["UnprocessedTemplateSvgFile"])
tree = ET.parse(unprocessedSvgTemplatePath)

root = tree.getroot()

#region Functions pasted from bot.py, code duplication is a bad habit, but I didn't have the heart to refacto all the project when I realised the bot couldn't be "self suficient"
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
    
#endregion

def get_rotation(node):
    if("transform" not in node.attrib): return 0
    transform_string=node.attrib["transform"]
    # Utiliser une expression régulière pour trouver la valeur de rotation
    rotation_match = re.search(r'rotate\((\d+)\)', transform_string)

    # Extraire la valeur si elle est trouvée
    if rotation_match:
        rotation_value = float(rotation_match.group(1))
    else:
        rotation_value = 0
    
    return rotation_value

#https://gist.github.com/james-roden/1164dea26b817ac5d5b3096621a7637b
def rotate_matrix (x, y, angle, x_shift=1, y_shift=1, units="DEGREES"):
    """
    Rotates a point in the xy-plane counterclockwise through an angle about the origin
    https://en.wikipedia.org/wiki/Rotation_matrix
    :param x: x coordinate
    :param y: y coordinate
    :param x_shift: x-axis shift from origin (0, 0)
    :param y_shift: y-axis shift from origin (0, 0)
    :param angle: The rotation angle in degrees
    :param units: DEGREES (default) or RADIANS
    :return: Tuple of rotated x and y
    """

    # Shift to origin (0,0)
    x = x - x_shift
    y = y - y_shift

    # Convert degrees to radians
    if units == "DEGREES":
        angle = math.radians(angle)

    # Rotation matrix multiplication to get rotated x & y
    xr = (x * math.cos(angle)) - (y * math.sin(angle)) + x_shift
    yr = (x * math.sin(angle)) + (y * math.cos(angle)) + y_shift

    return xr, yr

#Take in input the justification of Photoshop's artLayer's textContent, and output a value for the "text-anchor" of SVG
def justificationToTextAnchor(justification):
    if justification==photoshop.Justification.FullyJustified : return "middle"
    if justification==photoshop.Justification.Center : return "middle"
    if justification==photoshop.Justification.CenterJustified : return "middle"
    if justification==photoshop.Justification.Left : return "start"
    if justification==photoshop.Justification.LeftJustified : return "start"
    if justification==photoshop.Justification.Right : return "end"
    if justification==photoshop.Justification.RightJustified : return "end"

#We'll recursively find all text layers
def scanAllTextLayers(ps,parent, pathToParent, psdToSvgCoordinatesMultiplier:float):
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
        
        scanAllTextLayers(ps,child,pathToSelf, psdToSvgCoordinatesMultiplier)
        if(textComp==None):
            continue

        print("Text Layer: "+pathToSelf)
        photoshopLayer=get_layer_by_path(ps,pathToSelf)

        try:
            textAnchor=justificationToTextAnchor(photoshopLayer.textItem.justification)
            #now we must translate accordingly to corrate things
            textComp.attrib["text-anchor"]=textAnchor
            print("\t"+textAnchor)
        except:
            print("Couldn't get justification for "+pathToSelf)
            continue
        
        layerBounds=photoshopLayer.bounds
        layerWidth = layerBounds[2] - layerBounds[0]
        layerHeight = layerBounds[3] - layerBounds[1]

        deltaX=0
        deltaY=0
        if(textAnchor=="middle"):
            deltaX=0.5
        if(textAnchor=="end"):
            deltaX=1

        angle=get_rotation(textComp)
        xr, yr=rotate_matrix(deltaX,deltaY,angle,0,0)
        print("Angle :"+str(angle)+" xr"+str(xr)+" yr"+str(yr))
        translate_node(textComp,xr*layerWidth*psdToSvgCoordinatesMultiplier,yr*layerHeight*psdToSvgCoordinatesMultiplier,True)

with Session(os.path.join(os.getcwd(),settings["TemplatePsdFile"]), action="open", auto_close=True) as ps:
    svgHeight=root.attrib["height"]
    psdHeight=ps.active_document.height
    scanAllTextLayers(ps,root,"",float(svgHeight)/float(psdHeight))

output = BytesIO()
tree.write(output, encoding='utf-8', xml_declaration=True) 

svgTemplatePath=os.path.join(os.getcwd(),settings["TemplateSvgFile"])
with open(svgTemplatePath, "wb") as f:
    f.write(output.getbuffer())