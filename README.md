# 🎬 Auto Instagram — Daily Reels Generator

Automates the creation (and optional upload) of a daily 9:16 Instagram Reel
by randomly combining a background video, a music track, and a motivational quote.

---

## 📁 Project Structure

```
Auto_instagram/
├── reel_generator.py       # Core video composer (main script)
├── instagram_uploader.py   # Instagram Graph API uploader module
├── quotes.txt              # One motivational quote per line
├── requirements.txt        # Python dependencies
├── backgrounds/            # Place your .mp4 background clips here
└── music/                  # Place your .mp3 music tracks here
```

---

## ⚙️ Setup (Arch Linux)

### 1. Install system packages

```bash
sudo pacman -S python python-pip ffmpeg ttf-dejavu
```

> `ffmpeg` is required by MoviePy for video encoding.
> `ttf-dejavu` provides the **DejaVuSans-Bold** font used for text overlays.

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your assets

| Directory       | What to put there             |
|-----------------|-------------------------------|
| `./backgrounds/`| Abstract/colorful `.mp4` clips |
| `./music/`      | Instrumental `.mp3` tracks    |
| `quotes.txt`    | One quote per line            |

---

## 🚀 Usage

### Generate the daily reel

```bash
python reel_generator.py
```

Output: `daily_reel.mp4` (1080 × 1920, 10 s, H.264 + AAC)

### Upload to Instagram (optional)

1. Obtain a **long-lived User Access Token** and your **Instagram Business Account ID**
   from the [Meta for Developers](https://developers.facebook.com/) portal.

2. Open `instagram_uploader.py` and replace the placeholders:
   ```python
   ACCESS_TOKEN = "YOUR_LONG_LIVED_ACCESS_TOKEN_HERE"
   IG_USER_ID   = "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID"
   ```

3. Host `daily_reel.mp4` at a publicly accessible HTTPS URL
   (e.g. AWS S3, Cloudinary, Google Cloud Storage).

4. Call the uploader:
   ```python
   from instagram_uploader import upload_reel

   media_id = upload_reel(
       public_video_url="https://your-cdn.example.com/daily_reel.mp4",
       caption="✨ Daily motivation #motivation #mindset",
   )
   print(f"Published Reel ID: {media_id}")
   ```

---

## ⏰ Automate with Cron (daily at 09:00)

```bash
crontab -e
# Add the following line:
0 9 * * * cd /home/leo/Documents/proyects/Auto_instagram && .venv/bin/python reel_generator.py >> cron.log 2>&1
```

---

## 🎛️ Customisation

All key parameters live at the top of `reel_generator.py`:

| Variable        | Default                  | Description                    |
|-----------------|--------------------------|--------------------------------|
| `TARGET_W/H`    | 1080 × 1920              | Output resolution              |
| `REEL_DURATION` | 10 s                     | Video length                   |
| `AUDIO_FADEOUT` | 2 s                      | Fade-out duration at the end   |
| `FONT_PATH`     | DejaVuSans-Bold (Arch)   | Path to .ttf font              |
| `FONT_SIZE`     | 72 px                    | Quote text size                |
| `WRAP_WIDTH`    | 28 chars                 | Characters per line (wrapping) |

---

## 📋 Requirements

- Python ≥ 3.11
- MoviePy ≥ 2.0
- FFmpeg (system)
- DejaVu fonts (`ttf-dejavu` package)
