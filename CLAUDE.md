# Whatcha Know Wednesday: weekly editing playbook

This repo turns 1–2 raw MP4s into a finished "Whatcha Know Wednesday" episode for the
Alliance RV social channels. The user drops the footage; you do the edit.
The house style lives in `brand/style.yaml`. Read it, and stay consistent with past episodes in `weeks/`.

## The show format (from the 2026-10-07 Starlink episode)
- Vertical 1080x1920, about 25–35 s, one host talking to camera beside an Alliance RV unit.
- Opens on "Hey Allies, I'm excited for another Whatcha Know Wednesday. Today we're going to talk about <topic>."
  Keep that opener. It *is* the show's hook, so no text hook overlay by default (`hook.enabled: false`).
- Mid-episode **B-roll cutaways**: close-ups of the thing being discussed (ports, panels, labels) play while
  the host keeps talking. Add them via `broll` in the plan whenever the host says "this/these/here"
  or names a part and a close-up exists in the footage.
- Signs off with "So now you know." Then the last shot dips to black and the Alliance RV logo outro
  (`brand/assets/outro.mp4`, AllianceRV.com/Academy write-on) plays. The render adds both automatically.
- Captions: white Montserrat Black caps with a black outline; the spoken word sits on a cyan (#00C9E0) box.
- No music bed, no logo bug.

## When the user says "edit this week's WKW" (or sends footage / links)

1. **Get the footage in**
   - Uploaded in chat (lands under `/root/.claude/uploads/...`): `python -m wkw new`, then copy the files into
     `weeks/<date>/raw/`.
   - Links (Google Drive / Dropbox / direct): `python -m wkw new` prints the week folder, then
     `python -m wkw fetch weeks/<date> <url> [<url>]`.
   - Files already in `weeks/<date>/raw/` (local run or Git LFS push): use them as they are.
   - Clip order = filename order in `raw/`. Rename to `clip01`, `clip02`, ... if the user gives an order.
   - Pull a contact sheet of every clip first. If the footage already has burned-in captions or the logo outro,
     it is a finished episode, not raw footage: say so and ask for the raw clips. Re-editing it would stack
     a second set of captions on top. `weeks/2026-10-07-starlink-reference/` is one such reference.
2. **Transcribe + first-pass cut**: `python -m wkw auto weeks/<date>`
   This writes `transcript.json` (word timestamps) and `edit_plan.json` (silences and fillers removed).
3. **Do the real edit in `edit_plan.json`**. Read the transcript first. Then:
   - **Cut flubs and retakes.** When the host restarts a sentence, keep only the last clean take.
     Delete or trim segments: `start`/`end` are seconds in the source clip, `clip` is the index.
   - **Keep it tight.** Keep the "Hey Allies" opener and the "So now you know" sign-off. Cut rambles, keep 25–45 s.
     End the last segment right after "know" so the dip to black starts on time.
   - `broll`: `{"clip": i, "start": s, "end": e, "at": t}` puts source seconds s–e of clip i over the edit at
     t seconds (picture only, the host's voice continues). Find close-up shots by pulling a contact sheet of
     every clip; B-roll is often a separate clip, or the end of the main one.
   - `hook`: only used if `hook.enabled` is turned on in style.yaml.
   - `title`: thumbnail/cover text, 2–5 punchy words (e.g. "STARLINK VS STARLINK MINI").
   - `emphasis`: the 3–8 key terms (part names, numbers) drawn in the accent color.
   - `caption_fixes`: correct misheard brand/product words (Alliance RV, Paradigm, Avenue, Valor, Delta, MORryde, Starlink, etc.).
     Defaults already fix "What You Know Wednesday" and "pastry" (pass-through).
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
- `python tests/smoke_test.py` checks the whole render path without transcription. Run it after code changes.
