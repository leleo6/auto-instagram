import sys
import os
from pathlib import Path

# Setup project root correctly
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from bot_insta.src.core.video_engine import create_reel
from bot_insta.src.core.config_loader import config

config.set_active_profile("default")
p = create_reel()
print(f"Generated Reel: {p}")
