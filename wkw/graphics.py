"""All on-screen text (captions, hook, banner, end card) as one ASS subtitle file.

ASS keeps the look in one place, renders fast through ffmpeg's libass, and supports
the per-word pop/highlight that makes short-form captions feel alive.
"""
import re


def ass_color(hex_rgb, alpha=0):
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ts(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def clean(text):
    return re.sub(r"[{}\\]", "", text)


def timeline(plan):
    """Segments with their start on the edited timeline."""
    t, out = 0.0, []
    for s in plan["segments"]:
        out.append({**s, "out": t})
        t += s["end"] - s["start"]
    return out, t


def edited_words(plan, transcript):
    """Words that survived the cut, re-timed onto the edited timeline."""
    by_clip = {c["clip"]: c["words"] for c in transcript["clips"]}
    segs, _ = timeline(plan)
    fixes = {k.lower(): v for k, v in plan.get("caption_fixes", {}).items()}
    words = []
    for s in segs:
        for w in by_clip.get(s["clip"], []):
            mid = (w["s"] + w["e"]) / 2
            if s["start"] <= mid <= s["end"]:
                a = s["out"] + max(0.0, w["s"] - s["start"])
                b = s["out"] + min(s["end"], w["e"]) - s["start"]
                text = w["w"]
                key = re.sub(r"[^\w']", "", text.lower())
                if key in fixes:
                    text = re.sub(re.escape(key), fixes[key], text, flags=re.I)
                words.append({"w": text, "s": a, "e": b})
    # Apply multi-word fixes like "alliance rv" -> "Alliance RV" across neighbours.
    for phrase, repl in fixes.items():
        parts = phrase.split()
        if len(parts) < 2:
            continue
        i = 0
        while i <= len(words) - len(parts):
            got = [re.sub(r"[^\w']", "", words[i + j]["w"].lower()) for j in range(len(parts))]
            if got == parts:
                words[i] = {"w": repl, "s": words[i]["s"], "e": words[i + len(parts) - 1]["e"]}
                del words[i + 1:i + len(parts)]
            i += 1
    return words


def chunk(words, per_line):
    lines, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        gap = words[i + 1]["s"] - w["e"] if i + 1 < len(words) else 99
        if len(cur) >= per_line or gap > 0.35 or re.search(r"[.?!,]$", w["w"]):
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return lines


def build_ass(plan, transcript, style, width, height, offset=0.0, content_end=None, endcard=None):
    c, f, cap = style["colors"], style["fonts"], style["captions"]
    size = round(cap["size"] * height)
    accent, text, outline = ass_color(c["accent"]), ass_color(c["text"]), ass_color(c["outline"])
    primary = ass_color(c["primary"])
    cap_margin = round(height * (1 - cap["position_y"]))

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{f['caption']},{size},{text},{accent},{outline},&H60000000,0,0,0,0,100,100,1,0,1,{max(4, size // 11)},{max(3, size // 14)},2,70,70,{cap_margin},1
Style: CapBox,{f['caption']},{size},{text},{accent},{accent},&H00000000,0,0,0,0,100,100,1,0,3,{max(4, size // 10)},0,2,70,70,{cap_margin},1
Style: Hook,{f['caption']},{round(size * 1.35)},{text},{accent},{outline},&H80000000,0,0,0,0,100,100,1,0,1,{max(4, size // 9)},{max(2, size // 20)},5,80,80,0,1
Style: Banner,{f['title']},{round(size * 0.55)},{primary},{text},{accent},{accent},0,0,0,0,100,100,2,0,3,{round(size * 0.22)},0,8,60,60,{round(height * 0.08)},1
Style: End,{f['title']},{round(size * 0.9)},{text},{accent},{primary},&H00000000,0,0,0,0,100,100,1,0,1,0,0,5,80,80,0,1
Style: EndSub,{f['caption']},{round(size * 0.8)},{accent},{text},{primary},&H00000000,0,0,0,0,100,100,1,0,1,0,0,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    pop = r"{\fscx70\fscy70\t(0,120,\fscx100\fscy100)}"

    # Hook: banner + big question over the opening seconds.
    hook = style["hook"]
    hd = hook["duration"]
    if hook.get("enabled", True) and plan.get("hook") and not plan["hook"].startswith("TODO"):
        ev.append(f"Dialogue: 3,{ts(offset)},{ts(offset + hd)},Banner,,0,0,0,,{pop}{clean(hook['banner_text'])}")
        hook_txt = clean(plan["hook"].upper())
        ev.append(f"Dialogue: 3,{ts(offset + 0.15)},{ts(offset + hd)},Hook,,0,0,0,,"
                  rf"{{\pos({width // 2},{round(height * 0.30)})\fad(0,200)}}{pop}{hook_txt}")

    # Word-by-word captions. highlight "box": the spoken word sits on an accent-colored box
    # (house style); "color": the spoken word turns accent-colored.
    if cap["enabled"]:
        emph = {e.lower() for e in plan.get("emphasis", [])}
        mode = cap.get("highlight", "box")
        hide = r"{\alpha&HFF&}"
        for line in chunk(edited_words(plan, transcript), cap["words_per_line"]):
            end_line = line[-1]["e"] + 0.05
            words = [clean(x["w"].upper() if cap["uppercase"] else x["w"]) for x in line]
            if cap.get("strip_punctuation", True):
                words = [re.sub(r"[.,!?;:]+$", "", w) for w in words]
            for i, w in enumerate(line):
                start = w["s"]
                stop = line[i + 1]["s"] if i + 1 < len(line) else end_line
                base, box = [], []
                for j, word in enumerate(words):
                    is_emph = re.sub(r"[^\w']", "", line[j]["w"].lower()) in emph
                    active = j == i and cap["highlight_active_word"]
                    if active and mode == "color":
                        base.append(rf"{{\c{accent}}}{word}{{\c{text}}}")
                    elif is_emph and not active:
                        base.append(rf"{{\c{accent}}}{word}{{\c{text}}}")
                    else:
                        base.append(word)
                    # Box layer: same text so glyphs line up; only the active word is visible.
                    box.append(rf"{{\alpha&H00&}}{word}{hide}" if active else word)
                ev.append(f"Dialogue: 1,{ts(offset + start)},{ts(offset + stop)},Caption,,0,0,0,,{' '.join(base)}")
                if mode == "box" and cap["highlight_active_word"]:
                    ev.append(f"Dialogue: 2,{ts(offset + start)},{ts(offset + stop)},CapBox,,0,0,0,,{hide}{' '.join(box)}")

    # Generated end card (only when there is no outro video).
    if endcard and content_end is not None:
        a, b = content_end, content_end + endcard["duration"]
        ev.append(f"Dialogue: 4,{ts(a)},{ts(b)},End,,0,0,0,,{{\\pos({width // 2},{round(height * 0.45)})}}{pop}{clean(endcard['text'])}")
        ev.append(f"Dialogue: 4,{ts(a + 0.3)},{ts(b)},EndSub,,0,0,0,,{{\\pos({width // 2},{round(height * 0.55)})}}{pop}{clean(endcard['subtext'])}")

    return head + "\n".join(ev) + "\n"


def thumbnail_ass(plan, style, width, height):
    c, f = style["colors"], style["fonts"]
    size = round(height * 0.085)
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,{f['caption']},{size},{ass_color(c['text'])},{ass_color(c['accent'])},{ass_color(c['outline'])},&H80000000,0,0,0,0,100,100,1,0,1,{size // 9},{size // 18},5,70,70,0,1
Style: B,{f['title']},{round(size * 0.42)},{ass_color(c['primary'])},{ass_color(c['text'])},{ass_color(c['accent'])},{ass_color(c['accent'])},0,0,0,0,100,100,2,0,3,{size // 6},0,8,60,60,{round(height * 0.08)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 1,0:00:00.00,0:00:10.00,B,,0,0,0,,{clean(style['hook']['banner_text'])}
Dialogue: 1,0:00:00.00,0:00:10.00,T,,0,0,0,,{{\\pos({width // 2},{round(height * 0.33)})}}{clean(plan['title'].upper())}
"""
