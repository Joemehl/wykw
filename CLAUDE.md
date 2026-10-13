# Whatcha Know Wednesday: weekly editing playbook

This repo turns 1–2 raw MP4s into a finished "Whatcha Know Wednesday" episode for the
Alliance RV social channels. The user drops the footage; you do the edit.
The house style lives in `brand/style.yaml`. Read it, and stay consistent with past episodes in `weeks/`.

## When the user says "edit this week's WKW" (or sends footage / links)

1. **Get the footage in**
   - Links (Google Drive / Dropbox / direct): `python -m wkw new` prints the week folder, then
     `python -m wkw fetch weeks/<date> <url> [<url>]`.
   - Files already in `weeks/<date>/raw/` (local run or Git LFS push): use them as they are.
   - Clip order = filename order in `raw/`. Rename to `clip01`, `clip02`, ... if the user gives an order.
2. **Transcribe + first-pass cut**: `python -m wkw auto weeks/<date>`
   This writes `transcript.json` (word timestamps) and `edit_plan.json` (silences and fillers removed).
3. **Do the real edit in `edit_plan.json`**. Read the transcript first. Then:
   - **Cut flubs and retakes.** When the host restarts a sentence, keep only the last clean take.
     Delete or trim segments: `start`/`end` are seconds in the source clip, `clip` is the index.
   - **Open strong.** The first segment should be the most interesting line or the question. Reorder segments
     if the best hook comes later. Target 30–60 s of content (90 s max).
   - `hook`: a short question shown big over the first 3 s, at most about 8 words, e.g. "Do you know where your water heater bypass is?"
   - `title`: thumbnail text, 2–5 punchy words.
   - `emphasis`: the 3–8 key terms (part names, numbers) drawn in the accent color.
   - `caption_fixes`: correct misheard brand/product words (Alliance RV, Paradigm, Avenue, Valor, Delta, MORryde, etc.).
   - `thumbnail_time`: seconds into the edited content for a frame where the host's face/the part is clear.
   - `social.caption`: 1–3 friendly sentences plus a question that invites comments. Keep the hashtags.
   - Set `"status": "reviewed"`.
4. **Render**: `python -m wkw render weeks/<date>` produces `out/WKW_<date>_<format>.mp4`, a thumbnail, and `post.txt`.
5. **QC before delivering.** Pull a contact sheet and look at it:
   `ffmpeg -i out/<file>.mp4 -vf "fps=1/4,scale=270:-1,tile=6x2" -frames:v 1 <scratchpad>/sheet.png`.
   Check: the host isn't cropped off (adjust `framing.crop_center_x`), captions are readable and correctly
   spelled, no cut lands mid-word, and the end card shows.
6. **Deliver**: send the MP4(s), thumbnail and `post.txt` to the user with SendUserFile. Summarize the edit in
   a few lines (length, what was cut, the hook). Commit `transcript.json` + `edit_plan.json` (not video) to the
   working branch so future episodes can learn from past choices.

## Feedback
When the user critiques an episode ("captions too small", "always cut the intro wave"), change
`brand/style.yaml` or this playbook so the fix sticks for every future week. Don't only fix the one video.

## Constraints
- Never invent facts about RV systems in hooks or captions. Use only what the host says.
- Music must be a licensed track the user supplied (`brand/assets/music.mp3`). Never download music.
- Raw and rendered video stays out of git (see `.gitignore`).
- `python tests/smoke_test.py` checks the whole render path without Whisper. Run it after code changes.
