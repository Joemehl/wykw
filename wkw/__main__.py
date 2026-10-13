"""Whatcha Know Wednesday editor.

  python -m wkw new [DATE]                  create weeks/DATE/raw (DATE defaults to the next Wednesday)
  python -m wkw fetch WEEK URL [URL ...]    download share links (Google Drive / Dropbox / direct) into raw/
  python -m wkw transcribe WEEK             word-level transcript -> transcript.json
  python -m wkw plan WEEK                   first-pass cuts -> edit_plan.json (review before render)
  python -m wkw render WEEK [--format F]    edit_plan.json -> out/*.mp4, thumbnail, post.txt
  python -m wkw auto WEEK                   transcribe + plan in one go
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from .core import ROOT, Week, load_style, run


def next_wednesday(today=None):
    today = today or dt.date.today()
    return today + dt.timedelta(days=(2 - today.weekday()) % 7)


def week_arg(value):
    p = Path(value)
    if not p.exists() and (ROOT / "weeks" / value).exists():
        p = ROOT / "weeks" / value
    if not p.exists():
        raise SystemExit(f"no such week folder: {value}")
    return Week(p).ensure()


def direct_url(url):
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([\w-]+)", url)
    if m:
        return f"https://drive.usercontent.google.com/download?id={m.group(1)}&export=download&confirm=t"
    if "dropbox.com" in url:
        return re.sub(r"([?&])dl=0", r"\1dl=1", url) if "dl=" in url else url + ("&" if "?" in url else "?") + "dl=1"
    return url


def fetch(week, urls):
    for i, url in enumerate(urls, 1):
        out = week.raw / f"clip{len(week.clips()) + 1:02d}.mp4"
        print(f"  downloading {url} -> {out.name}")
        run(["curl", "-fL", "--retry", "3", "-o", str(out), direct_url(url)], quiet=False)
        if out.stat().st_size < 100_000 or b"<html" in out.read_bytes()[:2000].lower():
            out.unlink()
            raise SystemExit("got a web page instead of a video: make sure the link is shared as 'Anyone with the link'")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="wkw", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("date", nargs="?")
    p = sub.add_parser("fetch"); p.add_argument("week"); p.add_argument("urls", nargs="+")
    for name in ("transcribe", "plan", "auto"):
        sub.add_parser(name).add_argument("week")
    p = sub.add_parser("render"); p.add_argument("week"); p.add_argument("--format")
    args = ap.parse_args(argv)
    style = load_style()

    if args.cmd == "new":
        date = args.date or next_wednesday().isoformat()
        week = Week(ROOT / "weeks" / date).ensure()
        print(week.dir)
        return

    week = week_arg(args.week)
    if args.cmd == "fetch":
        fetch(week, args.urls)
        return
    if args.cmd in ("transcribe", "auto"):
        if not week.clips():
            raise SystemExit(f"no video files in {week.raw}")
        from .transcribe import transcribe
        transcribe(week, style)
    if args.cmd in ("plan", "auto"):
        from .plan import make_plan
        make_plan(week, style)
    if args.cmd == "render":
        from .render import render
        for o in render(week, style, only=args.format):
            print(o)


if __name__ == "__main__":
    sys.exit(main())
