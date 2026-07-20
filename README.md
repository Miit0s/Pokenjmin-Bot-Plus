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

---

## 3. Setting Up the Template Files

If you need to modify the card's design, you must edit the source files. 

### Step A: Photoshop & Illustrator
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

### Step B: Processing the SVG
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

## 4. Deployment

You can run the bot natively or in a container:

* **Manual:** Install dependencies and run `python bot.py`.
* **Docker:** *(Insert your standard Docker build/run commands here)*.

---

## 5. Final Export (Offline)

Because SVG generation causes slight visual/color loss, the final printable cards must be generated via Photoshop. **This requires a Windows computer with Photoshop 2020+, Python 3.12+, WSL, and Inkscape installed on WSL.**

### Step A: Retrieve Data from the Bot

1. On Discord, run the command `/export_all` and choose **JSON**.
2. The bot will send you `export.json` and several `.zip` files containing users' images.
3. Extract these zip files directly into `Data/CardImages` and `Data/OwnerPhotos`.

*If the zip files fail to send over Discord (due to size limits), retrieve them manually from your Docker container via SSH:*

```bash
# 1. Get your container ID
docker ps

# 2. Copy the image folders from the container to your host
sudo docker cp <container_id>:/usr/src/app/Data/CardImages ./CardImages
sudo docker cp <container_id>:/usr/src/app/Data/OwnerPhotos ./OwnerPhotos

# 3. Zip them to download them to your local Windows PC
sudo apt install zip
sudo zip -r CardImages.zip ./CardImages
sudo zip -r OwnerPhotos.zip ./OwnerPhotos
```

### Step B: Run the Photoshop Script

Place `export.json` in your local bot directory and run the exporter:

```bash
python export_to_photoshop.py export.json
```

This script will take over Photoshop, replace layers one by one, and output a high-quality, merged PDF ready for printing!