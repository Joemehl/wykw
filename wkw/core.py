"""Shared helpers: config loading, paths, ffmpeg/ffprobe wrappers."""
import json
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi"}


def load_style(path=None):
    with open(path or ROOT / "brand" / "style.yaml") as f:
        return yaml.safe_load(f)


def asset(style, key):
    """Path of an optional brand asset, or None when it hasn't been dropped in yet."""
    rel = style.get("assets", {}).get(key)
    p = ROOT / rel if rel else None
    return p if p and p.exists() else None


class Week:
    """weeks/<date>/raw (footage in), work (transcript, plan), out (deliverables)."""

    def __init__(self, folder):
        self.dir = Path(folder).resolve()
        self.raw = self.dir / "raw"
        self.work = self.dir / "work"
        self.out = self.dir / "out"
        self.transcript = self.dir / "transcript.json"
        self.plan = self.dir / "edit_plan.json"

    def ensure(self):
        for d in (self.raw, self.work, self.out):
            d.mkdir(parents=True, exist_ok=True)
        return self

    def clips(self):
        return sorted(p for p in self.raw.iterdir() if p.suffix.lower() in VIDEO_EXTS)


def run(cmd, quiet=True):
    if not shutil.which(cmd[0]):
        raise SystemExit(f"{cmd[0]} is not installed")
    res = subprocess.run(cmd, capture_output=quiet, text=True)
    if res.returncode != 0:
        tail = (res.stderr or "")[-3000:] if quiet else ""
        raise SystemExit(f"command failed: {' '.join(map(str, cmd[:6]))} ...\n{tail}")
    return res.stdout


def probe(path):
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    info = json.loads(out)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    w, h = (int(v["width"]), int(v["height"])) if v else (0, 0)
    # Phones store portrait video as landscape + a rotation flag.
    rot = 0
    if v:
        rot = int(v.get("tags", {}).get("rotate", 0) or 0)
        for sd in v.get("side_data_list", []):
            rot = int(sd.get("rotation", rot) or rot)
    if abs(rot) in (90, 270):
        w, h = h, w
    return {"duration": float(info["format"]["duration"]), "width": w, "height": h, "has_audio": a is not None}


def read_json(path):
    with open(path) as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
