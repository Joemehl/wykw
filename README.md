# WKW: Whatcha Know Wednesday auto-editor

Drop in 1–2 raw MP4s. Get back a captioned, jump-cut, branded vertical episode, a thumbnail and post copy.

```
raw clips ─► transcribe (Parakeet, word timing) ─► edit_plan.json ─► render
                                                   ▲ Claude edits:      ├─ WKW_<date>_vertical.mp4
                                                   │ cut flubs, hook,   ├─ WKW_<date>_vertical_thumb.jpg
                                                   │ title, emphasis    └─ post.txt (caption + hashtags)
```

What the render does: removes pauses and "um/uh", adds a slight punch-in on alternate jump cuts, lays B-roll
cutaways over the host's voice, burns in word-by-word captions with the spoken word on a cyan box, dips the
last shot to black into the Alliance RV logo outro, and sets loudness to -14 LUFS for social. Optional: hook
banner, logo bug, intro, ducked music bed.

## Weekly use (in Claude Code)

1. Open a Claude Code session on this repo and attach the raw MP4s (or paste Google Drive / Dropbox links
   shared as **"Anyone with the link"**), then say:
   > Edit this week's WKW. Topic is the water heater bypass. Clip 2 is B-roll of the valve.
2. Claude downloads, transcribes, edits, renders, checks the result, and sends you the files.
   Reply with notes ("tighter", "different hook") and Claude re-renders.

**Running locally instead** (Claude Code desktop/CLI on your computer, no upload needed): copy the MP4s into
`weeks/<date>/raw/` and say "edit this week's WKW".

## One-time setup

| Item | Where | Status |
|---|---|---|
| Transcription model (Parakeet, ~650 MB) | auto-downloads from GitHub on first run | works in cloud as is |
| Network: allow `drive.google.com`, `drive.usercontent.google.com` (or `dropbox.com`, `dl.dropboxusercontent.com`) | cloud environment settings → Network access | only for link intake; uploading in chat needs nothing |
| House style (captions, cyan #00C9E0, Montserrat Black) | `brand/style.yaml` | matched to the 2026-10-07 episode |
| Logo outro (AllianceRV.com/Academy) | `brand/assets/outro.mp4` | cut from the 2026-10-07 episode |
| Logo bug (transparent PNG) / intro sting | `brand/assets/logo.png`, `intro.mp4` | optional, not used by the show today |
| Licensed music bed | `brand/assets/music.mp3` | optional |

Fonts (Montserrat Black/ExtraBold, Anton, all under the SIL Open Font License) are bundled in `brand/fonts/`.

## Commands

```
python -m wkw new [DATE]              # create weeks/<next Wednesday>/raw
python -m wkw fetch WEEK URL...       # download share links into raw/
python -m wkw auto WEEK               # transcribe + first-pass plan
python -m wkw render WEEK             # plan -> deliverables in WEEK/out/
python tests/smoke_test.py            # end-to-end render check on synthetic footage
```

Add more output sizes (square feed, 16:9 YouTube) under `formats:` in `brand/style.yaml`.
