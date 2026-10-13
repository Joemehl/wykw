"""Turn edit_plan.json into finished deliverables.

Three passes, so memory stays flat no matter how long the raw footage is:
  1. each kept segment -> normalized intermediate (framing, punch-in, fps, audio)
  2. stream-copy concat (intro + segments + outro/end card)
  3. one finishing pass: captions/graphics, logo, music ducking, loudness
"""
from .core import ROOT, asset, probe, read_json, run
from .graphics import build_ass, thumbnail_ass, timeline

ENC_INTER = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
             "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
ENC_FINAL = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-profile:v", "high", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]


def fit_filter(style, W, H, zoom):
    fr = style["framing"]
    cx = fr.get("crop_center_x", 0.5)
    sw, sh = round(W * zoom / 2) * 2, round(H * zoom / 2) * 2
    if fr.get("fit") == "blur":
        return (f"split[bg][fg];[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3[bgb];"
                f"[fg]scale={sw}:{sh}:force_original_aspect_ratio=decrease[fgs];"
                f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,crop={W}:{H}")
    return (f"scale={sw}:{sh}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}:'(iw-{W})*{cx}':'(ih-{H})/2'")


def render_piece(src, start, dur, out, style, W, H, fps, zoom, has_audio, fade=True):
    vf = f"[0:v]{fit_filter(style, W, H, zoom)},fps={fps},setsar=1,format=yuv420p[v]"
    if has_audio:
        af = "[0:a]aresample=48000,aformat=channel_layouts=stereo"
        if fade:  # tiny fades stop clicks at jump cuts
            af += f",afade=t=in:d=0.02,afade=t=out:st={max(0, dur - 0.03):.3f}:d=0.03"
        af += f",apad,atrim=0:{dur:.3f}[a]"
        cmd = ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
               "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]"]
    else:
        cmd = ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
               "-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
               "-filter_complex", vf, "-map", "[v]", "-map", "1:a"]
    run(cmd + ["-t", f"{dur:.3f}"] + ENC_INTER + [str(out)])


def render_card(out, style, W, H, fps, dur):
    color = style["colors"]["primary"].lstrip("#")
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x{color}:s={W}x{H}:r={fps}:d={dur}",
         "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=48000:cl=stereo",
         "-map", "0:v", "-map", "1:a", "-t", str(dur)] + ENC_INTER + [str(out)])


def render(week, style, only=None):
    plan = read_json(week.plan)
    transcript = read_json(week.transcript)
    if plan.get("status") != "reviewed":
        print("  warning: edit_plan.json is still the automatic first pass (status != reviewed)")
    clips = week.clips()
    infos = [probe(p) for p in clips]
    intro, outro, logo, music = (asset(style, k) for k in ("intro", "outro", "logo", "music"))
    fonts_dir = ROOT / style["fonts"]["dir"]
    tag = week.dir.name
    outputs = []

    for fmt, spec in style["formats"].items():
        if only and fmt != only:
            continue
        W, H, fps = spec["width"], spec["height"], spec["fps"]
        tmp = week.work / fmt
        tmp.mkdir(parents=True, exist_ok=True)
        print(f"  [{fmt}] {W}x{H}")
        pieces, offset = [], 0.0

        if intro:
            i_info = probe(intro)
            p = tmp / "000_intro.mkv"
            render_piece(intro, 0, i_info["duration"], p, style, W, H, fps, 1.0, i_info["has_audio"], fade=False)
            pieces.append(p)
            offset = i_info["duration"]

        segs, content_len = timeline(plan)
        zoom = style["framing"].get("punch_in", 1.0)
        for k, s in enumerate(segs):
            dur = s["end"] - s["start"]
            z = zoom if (k % 2 == 1 and zoom > 1.0) else 1.0
            p = tmp / f"{k + 1:03d}_seg.mkv"
            render_piece(clips[s["clip"]], s["start"], dur, p, style, W, H, fps, z, infos[s["clip"]]["has_audio"])
            pieces.append(p)
        content_end = offset + content_len

        endcard = None
        if outro:
            o_info = probe(outro)
            p = tmp / "999_outro.mkv"
            render_piece(outro, 0, o_info["duration"], p, style, W, H, fps, 1.0, o_info["has_audio"], fade=False)
            pieces.append(p)
        else:
            endcard = style["endcard"]
            p = tmp / "999_endcard.mkv"
            render_card(p, style, W, H, fps, endcard["duration"])
            pieces.append(p)

        listing = tmp / "concat.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in pieces))
        joined = tmp / "joined.mkv"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined)])
        total = probe(joined)["duration"]

        ass_path = tmp / "graphics.ass"
        ass_path.write_text(build_ass(plan, transcript, style, W, H, offset=offset,
                                      content_end=content_end, endcard=endcard))

        # Finishing pass.
        inputs = ["-i", str(joined)]
        fc = [f"[0:v]ass='{ass_path}':fontsdir='{fonts_dir}'[vs]"]
        vlast = "vs"
        n = 1
        if logo:
            inputs += ["-i", str(logo)]
            lw = round(min(W, H) * 0.16)
            fc.append(f"[{n}:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa=0.9[lg]")
            fc.append(f"[{vlast}][lg]overlay=W-w-{round(W * 0.04)}:{round(H * 0.03)}"
                      f":enable='between(t,{offset:.2f},{content_end:.2f})'[vl]")
            vlast, n = "vl", n + 1

        a = style["audio"]
        fc.append("[0:a]highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120[voice]")
        alast = "voice"
        if music:
            inputs += ["-stream_loop", "-1", "-i", str(music)]
            fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},"
                      f"volume={a['music_volume']},afade=t=out:st={max(0, total - 1.5):.3f}:d=1.5[mus]")
            fc.append("[voice]asplit[v1][v2]")
            fc.append("[mus][v2]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[duck]")
            fc.append("[v1][duck]amix=inputs=2:duration=first:normalize=0[mix]")
            alast, n = "mix", n + 1
        fc.append(f"[{alast}]loudnorm=I={a['loudness_lufs']}:TP=-1.5:LRA=11,aresample=48000[aout]")

        final = week.out / f"WKW_{tag}_{fmt}.mp4"
        run(["ffmpeg", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", f"[{vlast}]", "-map", "[aout]",
                                          "-t", f"{total:.3f}"] + ENC_FINAL + [str(final)])
        outputs.append(final)

        # Thumbnail from the un-captioned edit.
        if plan.get("title") and not plan["title"].startswith("TODO"):
            th_ass = tmp / "thumb.ass"
            th_ass.write_text(thumbnail_ass(plan, style, W, H))
            thumb = week.out / f"WKW_{tag}_{fmt}_thumb.jpg"
            t = offset + float(plan.get("thumbnail_time", 1.0))
            run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(joined), "-frames:v", "1",
                 "-vf", f"ass='{th_ass}':fontsdir='{fonts_dir}'", "-q:v", "2", str(thumb)])
            outputs.append(thumb)
        print(f"  [{fmt}] done: {final.name} ({total:.1f}s)")

    social = plan.get("social", {})
    post = week.out / "post.txt"
    post.write_text(f"{plan.get('title', '')}\n\n{social.get('caption', '')}\n\n{' '.join(social.get('hashtags', []))}\n")
    outputs.append(post)
    return outputs
