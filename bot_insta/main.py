"""
main.py (GUI launcher)
─────────────────────────────────────────────────────────────────────────────
Starts the Auto Instagram Bot GUI application.
"""

import sys
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from bot_insta.src.gui.app import BotApp

if __name__ == "__main__":
    app = BotApp()
    app.mainloop()
