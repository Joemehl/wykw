# WKW: Whatcha Know Wednesday auto-editor

Drop in 1–2 raw MP4s. Get back a captioned, jump-cut, branded vertical episode, a thumbnail and post copy.

```
raw clips ─► transcribe (Whisper, word timing) ─► edit_plan.json ─► render
                                                   ▲ Claude edits:      ├─ WKW_<date>_vertical.mp4
                                                   │ cut flubs, hook,   ├─ WKW_<date>_vertical_thumb.jpg
                                                   │ title, emphasis    └─ post.txt (caption + hashtags)
```

What the render does: removes pauses and "um/uh", alternates 1.0×/1.12× punch-in on jump cuts, adds word-by-word
pop captions with the spoken word highlighted, a "WHATCHA KNOW WEDNESDAY" banner with a hook question over the
first 3 s, an optional logo bug, intro/outro, a ducked music bed, and loudness set to -14 LUFS for social.

## Weekly use (in Claude Code)

1. Upload the footage to Google Drive or Dropbox and share it as **"Anyone with the link"**.
2. Open a Claude Code session on this repo and say:
   > Edit this week's WKW: <link 1> <link 2>. Topic is the water heater bypass.
3. Claude downloads, transcribes, edits, renders, checks the result, and sends you the files.
   Reply with notes ("tighter", "different hook") and Claude re-renders.

**Running locally instead** (Claude Code desktop/CLI on your computer, no upload needed): copy the MP4s into
`weeks/<date>/raw/` and say "edit this week's WKW".

## One-time setup

| Item | Where | Status |
|---|---|---|
| Network: allow `huggingface.co` (Whisper model download) | cloud environment settings → Network access | **required for cloud** |
| Network: allow `drive.google.com`, `drive.usercontent.google.com` (or `dropbox.com`, `dl.dropboxusercontent.com`) | same | required for link intake |
| Brand colors, handle | `brand/style.yaml` | placeholders: replace |
| Logo (transparent PNG) | `brand/assets/logo.png` | optional |
| Intro / outro stings | `brand/assets/intro.mp4`, `outro.mp4` | optional (a generated end card is used otherwise) |
| Licensed music bed | `brand/assets/music.mp3` | optional |

Fonts (Anton, Montserrat ExtraBold, both under the SIL Open Font License) are bundled in `brand/fonts/`.

## Commands

```
python -m wkw new [DATE]              # create weeks/<next Wednesday>/raw
python -m wkw fetch WEEK URL...       # download share links into raw/
python -m wkw auto WEEK               # transcribe + first-pass plan
python -m wkw render WEEK             # plan -> deliverables in WEEK/out/
python tests/smoke_test.py            # end-to-end render check on synthetic footage
```

Add more output sizes (square feed, 16:9 YouTube) under `formats:` in `brand/style.yaml`.
