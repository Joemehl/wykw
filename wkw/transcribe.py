"""Word-level transcription of every raw clip with faster-whisper."""
from .core import ROOT, write_json


def transcribe(week, style):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("faster-whisper missing: pip install -r requirements.txt")

    name = style.get("transcription", {}).get("model", "small.en")
    try:
        model = WhisperModel(name, device="cpu", compute_type="int8", download_root=str(ROOT / ".models"))
    except Exception as e:  # usually the model download being blocked by the network
        raise SystemExit(
            f"could not load whisper model '{name}': {e}\n"
            "The model downloads from huggingface.co once; allow that host in the environment's network settings."
        )

    clips = []
    for i, path in enumerate(week.clips()):
        print(f"  transcribing {path.name} ...")
        segments, _ = model.transcribe(str(path), word_timestamps=True, vad_filter=True, language="en")
        words = []
        for seg in segments:
            for w in seg.words or []:
                words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)})
        clips.append({"clip": i, "file": path.name, "words": words,
                      "text": " ".join(w["w"] for w in words)})
    write_json(week.transcript, {"clips": clips})
    return clips
