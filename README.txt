Dependencies: 
photoshop-python-api: https://pypi.org/project/photoshop-python-api/; pip install photoshop-python-api
discord.py: https://pypi.org/project/discord.py/; pip install discord.py
pillow 10.4.0: https://pypi.org/project/pillow/; pip install pillow
pyvips: https://pypi.org/project/pyvips/; pip install pyvips

Copy the settings_template.json file, rename it "settings.json" then fill in your bot's Token.

HOW TO SET UP THE TEMPLATE FILES:

You should always make the psd in photoshop first, then you open it with Adobe Illstrator and export it to the .svg.
/!\ Dynamic layers names can't contain underscore or spaces or it won't work
Go to export (not save ! This won't produce the same kind of file) and choose export as SVG.
Set the decimals to 5, the maximum value, choose Inline Style for styling, and "SVG" for fonts. For the images choose "Link"
/!\ Only the visible layers will be exported to the svg, so make all the spe icons, watermarks, backgrounds etc. visible
/!\ Sometime Illustrator will ignore the name given to a layer in photoshop, make sure every name are the same

Exporting the stl directly from Photoshop will probably make a very broken svg.

Tip: Shape with large strokes, like the yellow border, will probably break in Illustrator, rasterize them in photoshop beforehand.
The svg template is a little lossy (especially on the color) so it should probably only be used for the preview. 
For the final export use the function of the bot that directly interacts with photoshop (so launch the bot from a Windows 10 computer)

Once your template is exported, run "process_template.py", this script will modify the svg template to add some finishing touches. 
You must repeat the process for each new export

HOW TO SETUP THE BOT:

Use this invite link and replace client_id with the client id of your bot:
https://discord.com/api/oauth2/authorize?client_id=[client_id]&permissions=277029161536&scope=bot