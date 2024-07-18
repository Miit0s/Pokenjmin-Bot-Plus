Dependencies: 
photoshop-python-api: https://pypi.org/project/photoshop-python-api/; pip install photoshop-python-api
discord.py: https://pypi.org/project/discord.py/; pip install discord.py
pillow 10.4.0: https://pypi.org/project/pillow/; pip install pillow

Copy the settings_template.json file, rename it "settings.json" then fill in your bot's Token.

HOW TO SET UP THE TEMPLATE FILES:

You should always make the psd in photoshop first, then you open it with Adobe Illstrator and export it to the .svg.
You should set Decimal Places to 7 (max value) and turn off every optimization option (Responsive, output fewer tspan elements...), as it may degrade your SVG's look
You should export with "Link" as image location in a folder that you will later fill in settings.json.
Untick "Preserve Illustrator Editing Capabilities" as it would make the SVG really heavy and basically unreadable by python
Exporting the stl directly from Photoshop will probably make a very broken svg.
Tip: Shape with large strokes, like the yellow border, will probably break in Illustrator, rasterize them in photoshop beforehand.
The svg template is a little lossy (especially on the color) so it should probably only be used for the preview. 
For the final export use the function of the bot that directly interacts with photoshop (so launch the bot from a Windows 10 computer)