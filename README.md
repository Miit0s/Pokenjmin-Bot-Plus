The Pokenjmin Bot Plus is a fork from the original bot by [Pordrack and tomdexp](https://github.com/Pordrack/Pokenjmin-Bot) with three main goals:
- Merge the old bot with the new changes made by the Master P21 that was not public
- Use fully open source software, and so fully dockable on Linux (f*ck Adobe)
- Improve the documentation so future promotions can set up the Discord bot more easily

# Pokenjmin Bot - Documentation & Setup Guide

Welcome to the Pokenjmin Bot Plus project! This bot allows Discord users to dynamically create and customize their own trading cards, with an export that uses CMYK (or CMJN in french) as color profile for high-quality printing.

---

## 0. Prerequisites & Dependencies

### Python Libraries
Install the required packages using `pip` (or via your `requirements.txt`):
* `discord.py` ([PyPI-Discord](https://pypi.org/project/discord.py/))
* `pillow` (version 10.4.0) ([PyPI-Pillow](https://pypi.org/project/pillow/))

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
4. **Watermark** In the `Specialties` array, change `WatermarkLayerName` to your current promotion (e.g. MasterP84). After that, go to the Section 3.

---

## 3. Setting Up the Template Files

If you need to modify the card's design, you must edit the source files. 

### Step 1: Krita

Krita handles all the static elements. Go to TemplateFile > Template_Pokenjmin.kra and make your changes. Once you are done, you can export your work as a .tiff (or .png if .tiff does not work).

### Step 2: Inkscape

As for Inkscape, it handles all the dynamic elements of the card, so everything that is modified by the user (text, card, owner image, ...) or by his specialty (background, the spe icons, ...). So if you want to change the text font, the speciality backgrounds, the speciality icons, etc., you’ll need to do it here.
⚠️ **Warning:** The layer structure and names are important, if you modify it, don't forget to reflect your changes in your settings.json or the bot will crash when trying to generate a preview.

For example, to add or modify the SVG file, here are the steps to add your promotion watermark:

1. Open the svg file in TemplateFile > Template_Pokenjmin.svg.
2. Go in the section `Layers and objects`, and open the group `Watermarks`.
3. Add your promotion watermark in it as an image (.png or .jpeg) with the name you put in `WatermarkLayerName` (e.g. MasterP84) in your settings.json.
> *Notes:* One way to import an image into Inkscape is to drag and drop it onto the canvas.
4. After that, position the watermark correctly where you want it to appear on the card.

---

## 4. Running the Bot

You can run the bot natively or easily deploy it using a Docker container.

### Option A: Manual

Install the dependencies listed in Section 0 and run `python bot.py`.

### Option B: Docker Compose (Recommended)

The easiest and cleanest way to run the bot is via Docker Compose.

1. Ensure Docker and Docker Compose are installed on your server/NAS.
2. Create the required host directories to match the volume bindings (e.g., `/volume1/docker/PokenjminBot/Data` and `/volume1/docker/PokenjminBot/Exports`).
3. Place your configured `settings.json` in the appropriate directory (`/volume1/docker/PokenjminBot/settings.json`).
4. Create a `docker-compose.yml` file by using the [compose-exemple.yml](compose-exemple.yml). Adapt it so that it works with your server.
> *Notes:* For exemple change the path from `/volume1/docker/PokenjminBot/Data` to one that works for you, like `/home/user/Documents/PokenjminBot/Data` for exemple.
5. Start the container in the background by running:

```bash
docker compose up -d
```

---

## 5. Final Export

With Pokenjmin Bot Plus, the final export can be simply done by executing the `/export_all` bot command with PDF as parameters. You can follow the progress in your Docker's log. When this is finished, all your cards will be available in the `Exports/PDF` folder you provided in your `docker-compose` file.