#!/usr/bin/env bash
# Script que ejecuta cli.py
cd "$(dirname "$0")/.."
source bot_insta/venv/bin/activate
python bot_insta/cli.py
