import sys, os
from pathlib import Path
_HERE = Path(os.getcwd())
PROJECT_ROOT = _HERE
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from bot_insta.src.core.video_engine import create_reel
from bot_insta.src.core.config_loader import config
config.set_active_profile("default")
p = create_reel()
print(f"Generated Reel: {p}")
