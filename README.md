# 🎬 Auto Instagram — Daily Reels Generator & Uploader

A robust, modular platform to automatically generate and upload daily vertical videos (Reels/Shorts/TikToks) with motivational quotes, background videos, and music. Includes a minimalist graphical interface (GUI).

---

## 🚀 Features
- **Video Generator:** Assembles highly engaging 9:16 videos natively using `moviepy 1.0.3` with wrapped, styled, and drop-shadow text overlays.
- **Graphic Interface (GUI):** A clean `customtkinter` dashboard to visually configure styles, manage profiles, preview the video layout live, and upload right from your screen.
- **Auto-Upload Integrations:** 
  - Instagram (via `instagrapi`)
  - YouTube (via `google-api-python-client`)
  - TikTok (via `tiktok-uploader`)
- **Profile Management:** Manage different visual identities, backgrounds, and settings directly via `config.yaml` or the GUI.
- **Robust Session Handling:** Preserves authentication tokens to prevent bot detection and avoids login blocks.

---

## 📁 Project Structure

```
auto-instagram/
├── bot_insta/
│   ├── assets/              # Place videos, music, and fonts here
│   ├── config/              # configuration (config.yaml) and session caches
│   ├── exports/             # Default folder for generated Reels
│   ├── src/                 # Source code (API modules, core engine, GUI)
│   ├── main.py              # GUI Launcher
│   └── requirements.txt     # Python dependencies
└── README.md
```

---

## ⚙️ Setup (Arch Linux / General Linux)

### 1. Install system packages

```bash
sudo pacman -S python python-pip ffmpeg
```

> `ffmpeg` is required by MoviePy for video encoding.

### 2. Create and activate a virtual environment

```bash
python -m venv bot_insta/venv
source bot_insta/venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r bot_insta/requirements.txt
```

### 4. Provide your Assets
Add some testing files so the bot has something to select from:
- `bot_insta/assets/backgrounds/`: Put vertical `.mp4`, `.mov` clips.
- `bot_insta/assets/music/`: Put `.mp3` tracks.
- `bot_insta/config/quotes.txt`: Put a quote on each line.

---

## 🎮 How to Use (Graphical Interface)

The whole core logic can be operated from a simple CustomTkinter Application.

### 1. Configure the Upload Variables (Instagram)

To keep your credentials private, the application expects them from your terminal session. If you intend to upload to instagram, export your username and password:

```bash
export INSTAGRAM_USERNAME="your_username"
export INSTAGRAM_PASSWORD="your_password"
```

*(Note: Once the first successful login happens, a `session.json` profile is preserved inside `bot_insta/config/` and these credentials might be skipped next time.)*

### 2. Launch the Application

Make sure your virtual environment is active, then launch the program:

```bash
python bot_insta/main.py
```

### 3. Usage inside the app
- Use the **Settings/Spec Editor View** on the right side to pick fonts, colors, stroke width, and audio volume. 
- You can preview it live.
- At the top left, select your publishing destination (`Local`, `Instagram`, `YouTube`, `TikTok`).
- Hit **Generate!** Watch the queue box process it async, and check the logs.

---

## 🎛️ Configurations

All GUI settings are serialized into `bot_insta/config/config.yaml`. Profiles allow you to keep multiple environments (for example, one for *Gym Motivation* and another for *Business Success*).

---

## 📋 Requirements
- Python ≥ 3.10
- MoviePy == 1.0.3
- FFmpeg (system)
- instagrapi (For Instagram module)
