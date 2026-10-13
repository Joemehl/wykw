"""End-to-end render check without Whisper: synthetic footage + a hand-made transcript.

  python tests/smoke_test.py      -> weeks/smoke-test/out/*.mp4
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from wkw.core import Week, load_style, probe, write_json  # noqa: E402
from wkw.plan import make_plan  # noqa: E402
from wkw.render import render  # noqa: E402

week = Week(ROOT / "weeks" / "smoke-test")
shutil.rmtree(week.dir, ignore_errors=True)
week.ensure()

# Two clips: a landscape "camera" clip with tone bursts (speech) and silences, and a short portrait clip.
burst = "0.4*sin(2*PI*220*t)*lt(mod(t\\,3)\\,2)"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=9",
                "-f", "lavfi", "-i", f"aevalsrc='{burst}':s=48000:d=9", "-shortest",
                "-c:v", "libx264", "-c:a", "aac", str(week.raw / "clip01.mp4")], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=720x1280:r=30:d=3",
                "-f", "lavfi", "-i", "sine=f=330:d=3", "-shortest",
                "-c:v", "libx264", "-c:a", "aac", str(week.raw / "clip02.mp4")], check=True)

said = "um so whatcha know about your alliance rv breaker panel uh here is the main breaker and the GFCI".split()
words, t = [], 0.2
for i, w in enumerate(said):
    if t % 3 > 2:  # skip the silent gap in each 3 s cycle
        t = (t // 3 + 1) * 3 + 0.1
    words.append({"w": w, "s": round(t, 2), "e": round(t + 0.32, 2)})
    t += 0.4
write_json(week.transcript, {"clips": [
    {"clip": 0, "file": "clip01.mp4", "words": words, "text": " ".join(said)},
    {"clip": 1, "file": "clip02.mp4", "words": [{"w": "Easy!", "s": 0.5, "e": 1.0}], "text": "Easy!"},
]})

style = load_style()
plan = make_plan(week, style)
plan.update(status="reviewed", title="Where's your breaker?", hook="Do you know where your breaker is?",
            emphasis=["GFCI", "breaker"], social={"caption": "Smoke test", "hashtags": ["#WhatchaKnowWednesday"]})
write_json(week.plan, plan)

outs = render(week, style)
for o in outs:
    print(o)
mp4 = [o for o in outs if o.suffix == ".mp4"][0]
info = probe(mp4)
assert (info["width"], info["height"]) == (1080, 1920), info
assert info["has_audio"] and info["duration"] > 5, info
print("OK", info)
