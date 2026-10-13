"""Build the first-pass edit plan from the transcript.

The plan is plain JSON on purpose: Claude (or you) reviews it, drops flubbed takes,
writes the hook/title/social copy, then `render` turns it into video.
"""
import re

from .core import probe, read_json, write_json


def _norm(word):
    return re.sub(r"[^a-z']", "", word.lower())


def auto_segments(words, duration, cut):
    """Keep speech, drop fillers and pauses longer than max_pause."""
    fillers = set(cut["fillers"])
    pad, max_pause, min_seg = cut["pad"], cut["max_pause"], cut["min_segment"]
    spoken = [w for w in words if _norm(w["w"]) not in fillers]
    segs = []
    for w in spoken:
        if segs and w["s"] - segs[-1]["end"] <= max_pause:
            segs[-1]["end"] = w["e"]
            segs[-1]["words"].append(w["w"])
        else:
            segs.append({"start": w["s"], "end": w["e"], "words": [w["w"]]})
    out = []
    for s in segs:
        start, end = max(0.0, s["start"] - pad), min(duration, s["end"] + pad)
        if end - start < min_seg:
            continue
        if out and start <= out[-1]["end"]:
            out[-1]["end"] = end
            out[-1]["text"] += " " + " ".join(s["words"])
        else:
            out.append({"start": round(start, 3), "end": round(end, 3), "text": " ".join(s["words"])})
    return out


def make_plan(week, style):
    transcript = read_json(week.transcript)
    clips = week.clips()
    segments = []
    for c in transcript["clips"]:
        dur = probe(clips[c["clip"]])["duration"]
        if not c["words"]:  # b-roll or silent clip: keep whole, Claude decides
            segments.append({"clip": c["clip"], "start": 0.0, "end": round(dur, 3), "text": "(no speech)"})
            continue
        for s in auto_segments(c["words"], dur, style["cutting"]):
            segments.append({"clip": c["clip"], **s})

    plan = {
        "status": "auto",  # Claude flips this to "reviewed" after editing the plan
        "title": "TODO episode title",
        "hook": "TODO scroll-stopping question",
        "segments": segments,
        "emphasis": [],
        "broll": [],  # cutaways: {"clip": i, "start": s, "end": e, "at": seconds into the edit}
        "caption_fixes": {"what you know wednesday": "Whatcha Know Wednesday", "watcha": "Whatcha",
                          "alliance rv": "Alliance RV", "rv": "RV", "rvs": "RVs", "pastry": "pass-through"},
        "thumbnail_time": 1.0,
        "social": {"caption": "", "hashtags": [style["show"]["hashtag"], "#AllianceRV", "#RVLife", "#RVTips"]},
    }
    write_json(week.plan, plan)
    kept = sum(s["end"] - s["start"] for s in segments)
    raw = sum(probe(p)["duration"] for p in clips)
    print(f"  plan: {len(segments)} segments, {kept:.1f}s kept of {raw:.1f}s raw")
    return plan
