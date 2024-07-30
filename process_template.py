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
#Node namespace, to add at the start of any node we create
nodeNamespace="ns0:"
#Same with atrib
attribNamespace="ns1:"
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

def getFontSizeFromStyle(style:str):
    pattern = r"font-size:\s*([\d.]+)px"
    match = re.search(pattern, style)
    fontSize=float(match.group(1))
    return fontSize

#Remove everything after a "_" in a layer id, keeping only the good part. But yes, it means we can't have "_" in the actual name of the id
def sanitizeLayerId(input:str):
    return input.split("_")[0]

#The tags are all prefixed by "{http://www.w3.org/2000/svg}", this function removes it
def sanitizeTag(input:str):
    return input.replace("{http://www.w3.org/2000/svg}","")  
#endregion

defsNode=None
for child in root:
    if(sanitizeTag(child.tag)=="defs"):
        defsNode=child


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

def remove_translation_from_node(node):
    #First we get and store the transform attribute
    transform=node.attrib["transform"]
    # Extraire les valeurs de translation
    translatePattern = r'translate\(([^)]+)\)'
    translateMatch = re.search(translatePattern, transform)
    if(translateMatch==None or translateMatch==False): return

    newTransformString=transform.replace(f"translate({translateMatch.group(1)})",f"")
    node.attrib["transform"]=newTransformString

def remove_rotation_from_node(node):
    #First we get and store the transform attribute
    transform=node.attrib["transform"]
    # Extraire les valeurs de translation
    translatePattern = r'rotate\(([^)]+)\)'
    translateMatch = re.search(translatePattern, transform)
    if(translateMatch==None or translateMatch==False): return

    newTransformString=transform.replace(f"rotate({translateMatch.group(1)})",f"")
    node.attrib["transform"]=newTransformString

#Take in input the justification of Photoshop's artLayer's textContent, and output a value for the "text-anchor" of SVG
def psdJustifToSvgTextAlign(justification):
    if justification==photoshop.Justification.FullyJustified : return "justify"
    if justification==photoshop.Justification.Center : return "center"
    if justification==photoshop.Justification.CenterJustified : return "justify"
    if justification==photoshop.Justification.Left : return "left"
    if justification==photoshop.Justification.LeftJustified : return "justify"
    if justification==photoshop.Justification.Right : return "right"
    if justification==photoshop.Justification.RightJustified : return "justify"

def psdColorToRgbHexCode(color):
    r = min(max(color.rgb.red, 0), 255)
    g = min(max(color.rgb.green, 0), 255)
    b = min(max(color.rgb.blue, 0), 255)
    return "#{:02X}{:02X}{:02X}".format(r, g, b)

txtCounter=0
#We'll recursively find all text layers
def scanAllTextLayers(ps,parent, pathToParent, psdToSvgCoordinatesMultiplier:float):
    global txtCounter
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
        txtCounter+=1

        print("Text Layer: "+pathToSelf)
        photoshopLayer=get_layer_by_path(ps,pathToSelf)

        #If we're on the card name layer we also calculate the multiplier from Photoshop's font size to svg font size, since it's the big zbeul
        if(pathToSelf==settings["CardNameLayer"]):
            svgFontSize=float(getFontSizeFromStyle(textComp.attrib["style"]))
            psdFontSize=float(photoshopLayer.textItem.size)
            scaleRatio=svgFontSize/psdFontSize
            root.attrib["fontScaleRatio"]=str(scaleRatio)

        tspans=0
        for child in textComp:
            if(sanitizeTag(child.tag)=="tspan"):
                tspans+=1
        isMultiline=(tspans>1)
        print("\t isMultiline="+str(isMultiline))    
        #Now that we have all the data that we need, we'll curate it to make it just like a InkScape Textbox, since the text node create by illustrator is a pain to interact with (no text alignement, no bounds etc.)
        # I don't know if it will work on other svg reader, but since we use InkScape for all our SVG needs...
        #First, we delete all the children, illustrator adds all sorts of nested tspan that are annoying to manage, we'll just pull the text from the psd and write it
        for child in list(textComp):
            textComp.remove(child)
        #All this attrib where copied from a text box created on InkScape, some of them may be useless
        textComp.attrib["xml:space"]="preserve"
        textComp.attrib["id"]="text"+str(txtCounter)
        textComp.attrib["inkscape:label"]="TextBox"+str(txtCounter)
        oldStyle=textComp.attrib["style"]
        if(oldStyle==None): oldStyle=""
        if(oldStyle!=""): oldStyle+=";"
        
        #For some layers, the photoshop API just crashed, every time it's for left aligned text layers, so it's no big deel
        textAlign="left"
        try:
            textAlign=psdJustifToSvgTextAlign(photoshopLayer.textItem.justification)
        except:
            print("\tCouldn't get justification for "+pathToSelf)
        
        newStyle=oldStyle
        newStyle+="font-stretch:condensed;line-height:0.8;text-align:"
        newStyle+=textAlign
        newStyle+=";white-space:pre;shape-inside:url(#"+"rect"+str(txtCounter)+");display:inline;fill:"
        newStyle+=psdColorToRgbHexCode(photoshopLayer.textItem.color)
        newStyle+=";fill-rule:evenodd;stroke-width:110;stroke-linecap:round;stroke-linejoin:round"
        #Now we account for rotation
        angle=get_rotation(textComp)
        remove_rotation_from_node(textComp)
        verticalLr=False
        if(angle!=90 and angle!=0):
            print("\t/!\Sadly the script doesnt support angle others than 90. It could tho, but you'll have to modify it and figure out how to apply a rotate transform with the good origin to not fuck up everything")
        #transform:"rotate(x)" works, but it mess up the position, I tried setting a different rotation origin transfrom:"rotate(x,ox,oy)", with the origin being the rect position, but it was just a bit off.
        #trying to compensate for it with a translate or by changing the rect position , but couldn't figure it out, so we just activate vertical lr mode if angle is equal to 90
        elif(angle==90):
            newStyle+=";writing-mode:vertical-lr"
            verticalLr=True

        textComp.attrib["style"]=newStyle
        textComp.text=photoshopLayer.textItem.contents
        #Now that the text is bound to a rect, it doesnt need to be translated through transform attribute anymore.
        remove_translation_from_node(textComp)
        
        #Now that the text comp itself is ok, we have to add a rect defining its bounds to the "def" node of the svg
        layerBounds=photoshopLayer.bounds
        layerX=psdToSvgCoordinatesMultiplier*layerBounds[0]
        layerY=psdToSvgCoordinatesMultiplier*layerBounds[1]
        layerWidth = psdToSvgCoordinatesMultiplier*layerBounds[2] - psdToSvgCoordinatesMultiplier*layerBounds[0]
        layerHeight = psdToSvgCoordinatesMultiplier*layerBounds[3] - psdToSvgCoordinatesMultiplier*layerBounds[1]

        #once again the angle/verticalLr thing is very messy/bruteforcy
        if(verticalLr):
            layerX-=0.25*layerWidth

        #But the bounds are too restrictive for our usage, firstly they're just a little bit too narrow on the height, which fucks up text printing for some reasons, and they're close to the sample text
        #So we open up one of their end, depending on their aligment/if they're multined
        #The single lined are jsut made wider in their "expending" direction whule the multilines one or expended downwards !
        #random big number
        expansionAmount=1000
        if(isMultiline):
            layerHeight+=expansionAmount
        #The vertical LR thing for the rotation is a little dirty, so in this state the program probably wont handle multiline AND vertical
        elif(verticalLr):
            #Actually no matter what it's just easier if the height is bigger, that way we don't have problems where the height is too narrow to print the text in InkScape
            layerHeight+=expansionAmount
            if(textAlign=="left"):
                layerWidth+=expansionAmount
            elif(textAlign=="right"):
                layerWidth+=expansionAmount
                layerY-=expansionAmount
            elif(textAlign=="center"):
                layerWidth+=2*expansionAmount
                layerX-=expansionAmount
        else:
            #Actually no matter what it's just easier if the height is bigger, that way we don't have problems where the height is too narrow to print the text in InkScape
            layerHeight+=expansionAmount
            if(textAlign=="left"):
                layerWidth+=expansionAmount
            elif(textAlign=="right"):
                layerWidth+=expansionAmount
                layerX-=expansionAmount
            elif(textAlign=="center"):
                layerWidth+=2*expansionAmount
                layerX-=expansionAmount

        rect=ET.SubElement(defsNode,nodeNamespace+"rect")
        rect.attrib={"x":str(layerX),"y":str(layerY),"width":str(layerWidth),"height":str(layerHeight),"id":("rect"+str(txtCounter))}

with Session(os.path.join(os.getcwd(),settings["TemplatePsdFile"]), action="open", auto_close=True) as ps:
    svgHeight=root.attrib["height"]
    psdHeight=ps.active_document.height
    #layer=ps.active_document.artLayers[0]
    scanAllTextLayers(ps,root,"",float(svgHeight)/float(psdHeight))

output = BytesIO()
tree.write(output, encoding='utf-8', xml_declaration=True) 

svgTemplatePath=os.path.join(os.getcwd(),settings["TemplateSvgFile"])
with open(svgTemplatePath, "wb") as f:
    f.write(output.getbuffer())