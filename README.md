# Pokenjmin Bot - Documentation & Setup Guide

Welcome to the Pokenjmin Bot project! This bot allows Discord users to dynamically create and customize their own trading cards, with an offline Photoshop export script for high-quality printing.

---

## 0. Prerequisites & Dependencies

### Python Libraries
Install the required packages using `pip` (or via your `requirements.txt`):
* `discord.py` ([PyPI-Discord](https://pypi.org/project/discord.py/))
* `pillow` (version 10.4.0) ([PyPI-Pillow](https://pypi.org/project/pillow/))
* `photoshop-python-api` ([PyPI-Photoshop-Python-API](https://pypi.org/project/photoshop-python-api/)) *(Required only for the final offline export)*

### System Requirements (Windows / WSL)
To guarantee 100% font accuracy between Discord previews and final renders (especially if users input "Zalgo" text), the final export relies on **Windows Subsystem for Linux (WSL)** with **Inkscape** and your project's fonts installed.
1. Install Inkscape on WSL: `sudo apt install inkscape`
2. Install the project's fonts (from the `Fonts` folder) onto your WSL system.
3. Launch WSL, navigate to the bot's directory, and run `./setup_script.sh`.
> *Tip: To make your WSL a perfect copy of your Docker container environment, check out [this tutorial](https://youtu.be/vgCkjPBL6Yk).*

---

## 1. Discord Bot Setup

Bots are tied to their developer's account. You must create your own application via the [Discord Developer Portal](https://discord.com/developers/applications).

1. Create a new Application.
2. In the **Bot** tab, enable all **Privileged Gateway Intents** (Presence, Server Members, and Message Content).
3. Get your Application ID (Client ID) from the **General Information** tab.
4. Invite the bot to your server using this URL (replace `[client_id]` with your actual ID):
   `https://discord.com/api/oauth2/authorize?client_id=[client_id]&permissions=277029161536&scope=bot`

---

## 2. Configuration (`settings.json`)

1. Duplicate `settings_template.json` and rename it to `settings.json`.
2. **Bot Token:** Paste your token (found in the Bot tab of the Developer Portal) into the JSON.
3. **Admins:** Add the Discord IDs of your admins in the `Admins` array. (Admins are the only ones who can modify legendary cards and use setup commands).
> *Note:* `CardNameFontSize` Min and Max are expressed in `px` based on the PSD. Don't worry about the SVG having completely different font size values; `process_template.py` calculates the ratio automatically.
4. **Watermark** In the `Specialties` array, change the `WatermarkLayerName` by your current promotion (e.g. MasterP84). After that, go to the 3. section.

---

## 3. Setting Up the Template Files

If you need to modify the card's design, you must edit the source files. 

### Option 1: Inkscape

1. Open the svg file in TemplateSVG > Template_Pokenjmin.svg.
2. Go in the section `Layers and objects`, and open the group g3 > Watermarks.
3. Create a new group with the name you put in `WatermarkLayerName` (e.g. MasterP84), and add your promotion watermark in it as a image (.png or .jpeg).
   * ⚠️ **Warning:** You need to change the group label AND id. For that go in Object Properties (Maj+Ctrl+O) and change the `ID` and `Label` settings.
> *Notes:* One way to import an image into Inkscape is to drag and drop it onto the canvas.
4. After that, position the watermark correctly where you want it to appear on the map.

### Option 2: Photoshop & Illustrator

**Step A: Design Export**

1. Make your design changes in `Template_Pokenjmin.psd`.
   * ⚠️ **Warning:** Dynamic layer names **must not** contain underscores (`_`) or spaces!
   * *Tip:* Rasterize complex shapes with large strokes (like yellow borders) in Photoshop before moving to Illustrator.
2. Open the PSD in **Adobe Illustrator**.
   * ⚠️ *Make sure Illustrator hasn't ignored any layer names from Photoshop.*
3. Make all dynamic layers visible (spe icons, watermarks, backgrounds, etc.). Hidden layers will NOT be exported!
4. Go to `File > Export > Export As...` and choose **SVG**.
   * **Decimals:** `5` (Maximum)
   * **Styling:** `Inline Style`
   * **Font:** `SVG`
   * **Images:** `Link`
5. Save the file as `TemplateSVG/Template_Pokenjmin_Unprocessed.svg`. *(Clear the folder beforehand to avoid old PNGs piling up).*

**Step B: Processing the SVG**

Exporting directly from Illustrator leaves the SVG broken for dynamic text insertion. You must run the Python processing script:
```bash
python3 process_template.py
```

**What this script does:**

* Changes the `text-anchor` property to reflect PSD alignment.
* Translates text to avoid shifting (currently bruteforced, so manual tweaks may be needed for fancy angles).
* ⚠️ *Ensure your Photoshop unit preferences (Preferences -> Rulers & Units) are set to **"Points"**, otherwise the script's PSD-to-SVG font size math will fail.*

The resulting file will be saved as `TemplateSVG/Template_Pokenjmin.svg`. **You must repeat Step A and B every time you alter the visual design.**

---

You can run the bot natively or easily deploy it using a Docker container.

### Option A: Manual

Install the dependencies listed in Section 0 and run `python bot.py`.

### Option B: Docker Compose (Recommended)

The easiest and cleanest way to run the bot is via Docker Compose.

1. Ensure Docker and Docker Compose are installed on your server/NAS.
2. Create the required host directories to match the volume bindings (e.g., `/volume1/docker/PokenjminBot/Data` and `/volume1/docker/PokenjminBot/Exports`).
3. Place your configured `settings.json` in the appropriate directory (`/volume1/docker/PokenjminBot/settings.json`).
4. Create a `docker-compose.yml` file by using the [compose-exemple.yml](compose-exemple.yml). Adapt it so that it works with your server.
> *Notes:* For exemple change the path from `/volume1/docker/PokenjminBot/Data` to one that work for you, like `/home/user/Documents/PokenjminBot/Data` for exemple.
5. Start the container in the background by running:

```bash
docker compose up -d
```

---

## 5. Final Export (Offline)

Because SVG generation causes slight visual/color loss, the final printable cards must be generated via Photoshop. **This requires a Windows computer with Photoshop 2020+, Python 3.12+, WSL, and Inkscape installed on WSL.**

### Step A: Retrieve Data from the Bot

1. On Discord, run the command `/export_all` and choose **JSON**.
2. The bot will send you `export.json` and several `.zip` files containing users' images.
3. Extract these zip files directly into `Data/CardImages` and `Data/OwnerPhotos`.

*If the zip files fail to send over Discord (due to size limits):*
Thanks to your Docker Compose volume bindings, the generated files are already accessible directly on your host machine without needing to interact with the container.

1. Connect to your host server/NAS.
2. Navigate to your mapped `Data` directory (e.g., `/volume1/docker/PokenjminBot/Data`) and download the data.

### Step B: Run the Photoshop Script

Place `export.json` in your local bot directory and run the exporter:

```bash
python export_to_photoshop.py export.json
```

This script will take over Photoshop, replace layers one by one, and output a high-quality, merged PDF ready for printing!