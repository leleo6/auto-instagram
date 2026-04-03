"""
style.py
─────────────────────────────────────────────────────────────────────────────
CustomTkinter styling variables and fonts definitions based on Teal/Gold aesthetic.
"""

from bot_insta.src.core.config_loader import config

THEME_MODE = config.get("gui", "theme", "dark")
BG_COLOR = config.get("gui", "bg_color", "#1e1e24")
ACCENT_GOLD = config.get("gui", "accent_gold", "#FFD700")
ACCENT_TEAL = config.get("gui", "accent_teal", "#008080")
TEXT_COLOR = "white"

FONT_MAIN = ("Inter", 14)
FONT_TITLE = ("Inter", 18, "bold")
FONT_SMALL = ("Inter", 12)
