import customtkinter as ctk
from pathlib import Path
from bot_insta.src.gui.style import THEME_MODE

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

def init_app_theme():
    ctk.set_appearance_mode(THEME_MODE)
    ctk.set_default_color_theme("green")

def scan_fonts() -> dict[str, str]:
    """Returns {display_name: full_path} for all .ttf/.otf on the system."""
    font_dirs = [
        Path("/usr/share/fonts"),
        Path.home() / ".local/share/fonts",
        PROJECT_ROOT / "bot_insta/assets/fonts",
    ]
    fonts = {}
    for d in font_dirs:
        if not d.exists(): continue
        for f in sorted(d.rglob("*")):
            if f.suffix.lower() in (".ttf", ".otf"):
                fonts[f.stem] = str(f)
    return fonts

SYSTEM_FONTS = scan_fonts()
