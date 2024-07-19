Dependencies: 
photoshop-python-api: https://pypi.org/project/photoshop-python-api/; pip install photoshop-python-api
discord.py: https://pypi.org/project/discord.py/; pip install discord.py
pillow 10.4.0: https://pypi.org/project/pillow/; pip install pillow

sudo apt install inkscape (if not on Linux, install inkscape and add it to your PATH variable, or use the WSL)

HOW TO SETUP THE BOT:

Since a bot is tied to its developper, you can't reuse the bot of the previous years (except if you ask very nicely). 
Create your own bot using the Discord Application Portal.

Use this invite link and replace client_id with the Application ID of your bot, you can get it in the General tab of your application's page on the developper portal:
https://discord.com/api/oauth2/authorize?client_id=[client_id]&permissions=277029161536&scope=bot

In the Bot tab of the developper portal you'll see several switches describing "Privileged Gateway Intents", in doubt, activate them all, it can't hurt.


HOW TO SET UP THE TEMPLATE FILES:

You should always make the psd in photoshop first, then you open it with Adobe Illstrator and export it to the .svg.
/!\ Dynamic layers names can't contain underscore or spaces or it won't work
Go to export (not save ! This won't produce the same kind of file) and choose export as SVG.
Set the decimals to 5, the maximum value, choose Inline Style for styling, and "SVG" for fonts. For the images choose "Link"
/!\ Only the visible layers will be exported to the svg, so make all the spe icons, watermarks, backgrounds etc. visible
/!\ Sometime Illustrator will ignore the name given to a layer in photoshop, make sure every name are the same

Exporting the svg directly from Photoshop will probably make a very broken svg.

Tip: Shape with large strokes, like the yellow border, will probably break in Illustrator, rasterize them in photoshop beforehand.
The svg template is a little lossy (especially on the color) so it should probably only be used for the preview. 
For the final export use the function of the bot that directly interacts with photoshop (so launch the bot from a Windows 10 computer)

Once your template is exported, run "process_template.py", this script will modify the svg template to add some finishing touches. 
You must repeat the process for each new export


HOW TO SETUP THE SETTINGS:
Copy and paste "settings_template.json" and rename it "settings.json", in the admins part of the json, paste all the Discord IDs (the big number you get by shift->right clicking on someone) of your admins there.
The admins are the only persons allowed to modify legendary cards and other users cards, they are also responsible for setting up some settings.
Get your bot Token in the "Bot" tab of the developer portal and past it as your Bot Token.

HOW TO DEPLOY:

[Insert Docker Tutorial Here]
Alternatively you can just manually install the dependancies and run bot.py as is.


HOW TO EXPORT:

Since the preview system that uses SVG is a bit hasardous and cause loss to the file, we reccomend you make the export using photoshop directly. It's very long, and it only works if the bot is running on a Windows PC with Photoshop installed.
Pull the latest database, grab a coke, turn off the server's version of the bot, send a slash command and wait for about an hour (give or take).