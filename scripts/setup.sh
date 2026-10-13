#!/usr/bin/env bash
# Installs what the editor needs. Runs automatically at the start of each cloud session.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v ffmpeg >/dev/null || { echo "ffmpeg missing: install it (apt-get install ffmpeg / brew install ffmpeg)"; exit 1; }
python3 -c "import faster_whisper, yaml" 2>/dev/null || python3 -m pip install -q -r requirements.txt
