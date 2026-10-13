"""Word-level transcription of every raw clip.

Backends (brand/style.yaml -> transcription.backend):
  parakeet: NVIDIA Parakeet TDT 0.6B via sherpa-onnx. Default. Its model downloads from GitHub
            releases, which works in the cloud environment without extra network allowances.
  whisper:  faster-whisper. Needs huggingface.co reachable for its model download.
"""
import subprocess
import tarfile
import urllib.request

import numpy as np

from .core import ROOT, write_json

MODELS = ROOT / ".models"
RELEASES = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
PARAKEET = "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8"
SR = 16000


def _download(url, dest):
    print(f"  downloading {url.rsplit('/', 1)[-1]} (one time) ...")
    MODELS.mkdir(exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dest)


def _load_audio(path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768


def _parakeet():
    import sherpa_onnx

    d = MODELS / PARAKEET
    if not (d / "tokens.txt").exists():
        archive = MODELS / f"{PARAKEET}.tar.bz2"
        _download(RELEASES + archive.name, archive)
        with tarfile.open(archive) as t:
            t.extractall(MODELS, filter="data")
        archive.unlink()
    vad_path = MODELS / "silero_vad.onnx"
    if not vad_path.exists():
        _download(RELEASES + "silero_vad.onnx", vad_path)

    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(d / "encoder.int8.onnx"), decoder=str(d / "decoder.int8.onnx"),
        joiner=str(d / "joiner.int8.onnx"), tokens=str(d / "tokens.txt"),
        model_type="nemo_transducer", num_threads=4)

    def speech_chunks(audio):
        """Split long audio at pauses so each decode stays short; returns (offset_s, samples)."""
        cfg = sherpa_onnx.VadModelConfig()
        cfg.silero_vad.model = str(vad_path)
        cfg.silero_vad.min_silence_duration = 0.4
        cfg.silero_vad.max_speech_duration = 25
        cfg.sample_rate = SR
        vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=600)
        win = cfg.silero_vad.window_size
        for i in range(0, len(audio), win):
            vad.accept_waveform(audio[i:i + win])
        vad.flush()
        while not vad.empty():
            seg = vad.front
            yield seg.start / SR, np.array(seg.samples, dtype=np.float32)
            vad.pop()

    def run(path):
        words = []
        for offset, samples in speech_chunks(_load_audio(path)):
            # Pad so words at the chunk edges decode cleanly.
            pad = np.zeros(int(0.3 * SR), dtype=np.float32)
            s = rec.create_stream()
            s.accept_waveform(SR, np.concatenate([pad, samples, pad]))
            rec.decode_stream(s)
            r = s.result
            base = offset - 0.3
            durs = list(r.durations) if getattr(r, "durations", None) else [0.08] * len(r.tokens)
            for tok, t0, dur in zip(r.tokens, r.timestamps, durs):
                start, end = base + t0, base + t0 + max(dur, 0.04)
                if tok.startswith(" ") or not words:
                    if tok.strip() in {",", ".", "?", "!"} and words:
                        words[-1]["w"] += tok.strip()
                        continue
                    words.append({"w": tok.strip(), "s": start, "e": end})
                else:  # continuation of the current word (sub-word piece or punctuation)
                    words[-1]["w"] += tok
                    words[-1]["e"] = end
        for w in words:
            w["s"], w["e"] = round(max(0.0, w["s"]), 3), round(w["e"], 3)
        return [w for w in words if w["w"]]

    return run


def _whisper(name):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("faster-whisper missing: pip install faster-whisper")
    try:
        model = WhisperModel(name, device="cpu", compute_type="int8", download_root=str(MODELS))
    except Exception as e:
        raise SystemExit(f"could not load whisper model '{name}': {e}\n(needs huggingface.co reachable)")

    def run(path):
        segments, _ = model.transcribe(str(path), word_timestamps=True, vad_filter=True, language="en")
        return [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)}
                for seg in segments for w in (seg.words or [])]

    return run


def transcribe(week, style):
    cfg = style.get("transcription", {})
    backend = cfg.get("backend", "parakeet")
    run = _whisper(cfg.get("model", "small.en")) if backend == "whisper" else _parakeet()
    clips = []
    for i, path in enumerate(week.clips()):
        print(f"  transcribing {path.name} ({backend}) ...")
        words = run(path)
        clips.append({"clip": i, "file": path.name, "words": words, "text": " ".join(w["w"] for w in words)})
    write_json(week.transcript, {"clips": clips})
    return clips
