"""Step 2a: transcribe speech with NVIDIA Parakeet (TDT 0.6B v3, run locally via ONNX).

Usage:
  python tools/scripts/transcribe.py <project> [--file NAME] [--speakers auto|N] [--force]

For every file in raw/<project>/ with audio, writes to transcripts/<project>/:
  <stem>.json  word-level timestamps (seconds in the source file), confidence, speaker
  <stem>.md    readable transcript, one line per phrase, with timestamps and
               "POSSIBLE RETAKE" flags where a phrase restarts an earlier one
Files with fewer than 5 words per minute are marked "no speech" so they go to the
shot log instead.
"""

import argparse
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from common import MODELS, ROOT, fmt_time, project_dir, raw_files, write_json

PARAKEET = MODELS / "parakeet-tdt-0.6b-v3"
SILERO = MODELS / "silero-vad"
DIAR_SEG = MODELS / "diarization" / "segmentation.onnx"
DIAR_EMB = MODELS / "diarization" / "embedding.onnx"
FRAME = 0.08  # Parakeet token time resolution (seconds)


def extract_wav(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "pcm_s16le", str(dst)], check=True)


def load_asr():
    import onnx_asr
    if not (PARAKEET / "config.json").exists():
        sys.exit(f"Parakeet model not found in {PARAKEET}. Run: bash tools/setup.sh")
    quant = "int8" if (PARAKEET / "encoder-model.int8.onnx").exists() else None
    asr = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", str(PARAKEET), quantization=quant)
    vad = onnx_asr.load_vad("silero", str(SILERO))
    return asr.with_vad(vad, max_speech_duration_s=25, min_silence_duration_ms=250).with_timestamps()


def words_from_segment(seg) -> list[dict]:
    """Group Parakeet sub-word tokens into words with absolute start/end times."""
    words, cur = [], None
    toks, times = seg.tokens or [], seg.timestamps or []
    probs = seg.logprobs or [0.0] * len(toks)
    for tok, t, lp in zip(toks, times, probs):
        starts_word = tok.startswith((" ", "▁"))
        text = tok.replace("▁", " ")
        if cur is None or (starts_word and text.strip()):
            if cur:
                words.append(cur)
            cur = {"w": text.strip(), "s": seg.start + t, "last": seg.start + t, "lp": [lp]}
        else:
            cur["w"] += text.strip() if not cur["w"] else text
            cur["last"] = seg.start + t
            cur["lp"].append(lp)
    if cur:
        words.append(cur)
    out = []
    for i, w in enumerate(words):
        nxt = words[i + 1]["s"] if i + 1 < len(words) else seg.end
        end = min(w["last"] + 2 * FRAME, nxt, seg.end)
        conf = math.exp(sum(w["lp"]) / len(w["lp"])) if w["lp"] else 1.0
        if w["w"]:
            out.append({"w": w["w"], "s": round(w["s"], 3), "e": round(max(end, w["s"] + 0.04), 3),
                        "conf": round(conf, 3)})
    return out


def diarize(wav: Path, speakers: str) -> list[tuple[float, float, int]]:
    import sherpa_onnx as so
    if not (DIAR_SEG.exists() and DIAR_EMB.exists()):
        print("  ! Speaker models missing (run tools/setup.sh); skipping speaker labels.")
        return []
    n = -1 if speakers == "auto" else int(speakers)
    cfg = so.OfflineSpeakerDiarizationConfig(
        segmentation=so.OfflineSpeakerSegmentationModelConfig(
            pyannote=so.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(DIAR_SEG))),
        embedding=so.SpeakerEmbeddingExtractorConfig(model=str(DIAR_EMB)),
        clustering=so.FastClusteringConfig(num_clusters=n, threshold=0.6),
        min_duration_on=0.3, min_duration_off=0.5,
    )
    sd = so.OfflineSpeakerDiarization(cfg)
    audio, sr = sf.read(str(wav), dtype="float32")
    assert sr == sd.sample_rate
    return [(s.start, s.end, s.speaker) for s in sd.process(audio).sort_by_start_time()]


def assign_speakers(words: list[dict], turns) -> None:
    for w in words:
        best, best_ov = None, 0.0
        for s, e, spk in turns:
            ov = min(e, w["e"]) - max(s, w["s"])
            if ov > best_ov:
                best, best_ov = spk, ov
        if best is None and turns:  # nearest turn
            best = min(turns, key=lambda t: min(abs(t[0] - w["s"]), abs(t[1] - w["s"])))[2]
        w["spk"] = f"S{best + 1}" if best is not None else None


def phrases(words: list[dict], gap: float = 0.6, max_len: float = 12.0) -> list[dict]:
    """Split words into readable phrases at pauses, sentence ends, or speaker changes."""
    out, cur = [], []
    for w in words:
        if cur and (w["s"] - cur[-1]["e"] > gap or w.get("spk") != cur[-1].get("spk")
                    or w["s"] - cur[0]["s"] > max_len
                    or (cur[-1]["w"][-1:] in ".?!" and w["s"] - cur[-1]["e"] > 0.25)):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return [{"s": p[0]["s"], "e": p[-1]["e"], "spk": p[0].get("spk"), "i0": p[0]["i"], "i1": p[-1]["i"],
             "text": " ".join(x["w"] for x in p)} for p in out]


def norm(text: str) -> list[str]:
    return re.sub(r"[^\w\s']", "", text.lower()).split()


def flag_retakes(ph: list[dict]) -> None:
    """Mark a phrase as a likely retake when a later phrase (within 45 s) starts the same way."""
    for i, p in enumerate(ph):
        a = norm(p["text"])[:4]
        if len(a) < 3:
            continue
        for q in ph[i + 1:]:
            if q["s"] - p["s"] > 45:
                break
            if norm(q["text"])[:len(a)] == a:
                p["retake_of_later"] = q["i0"]
                break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--file", help="only this file (name inside raw/<project>/)")
    ap.add_argument("--speakers", default=None, help="'auto' or a number to label speakers")
    ap.add_argument("--force", action="store_true", help="redo files that already have a transcript")
    a = ap.parse_args()

    out = project_dir("transcripts", a.project)
    files = [f for f in raw_files(a.project) if not a.file or f.name == a.file]
    asr = None
    for f in files:
        dst = out / f"{f.stem}.json"
        if dst.exists() and not a.force:
            print(f"  {f.name}: already transcribed")
            continue
        wav = out / ".cache" / f"{f.stem}.wav"
        try:
            extract_wav(f, wav)
        except subprocess.CalledProcessError:
            print(f"  {f.name}: no audio track, skipped")
            continue
        duration = sf.info(str(wav)).duration
        print(f"  {f.name}: transcribing {fmt_time(duration)}…", flush=True)
        asr = asr or load_asr()
        words = []
        for seg in asr.recognize(str(wav)):
            words.extend(words_from_segment(seg))
        for i, w in enumerate(words):
            w["i"] = i
        if a.speakers:
            assign_speakers(words, diarize(wav, a.speakers))
        wpm = len(words) / max(duration / 60, 1e-6)
        ph = phrases(words)
        flag_retakes(ph)
        speakers = sorted({w.get("spk") for w in words if w.get("spk")})
        write_json(dst, {"file": str(f.relative_to(ROOT)), "duration": round(duration, 3), "has_speech": wpm >= 5, "words_per_minute": round(wpm, 1),
                         "speakers": speakers, "words": words, "phrases": ph})

        lines = [f"# Transcript: {f.name}", "",
                 f"Length {fmt_time(duration)} · {len(words)} words · {wpm:.0f} wpm"
                 + (f" · speakers: {', '.join(speakers)}" if speakers else "")
                 + ("" if wpm >= 5 else " · **NO SPEECH — use the shot log**"), "",
                 "Format: [start–end] #first-word-index (speaker) text. Low-confidence words are marked ~like~ this.", ""]
        for p in ph:
            text = " ".join(f"~{w['w']}~" if w["conf"] < 0.5 else w["w"] for w in words[p["i0"]:p["i1"] + 1])
            spk = f" ({p['spk']})" if p.get("spk") else ""
            flag = f"  ⟲ POSSIBLE RETAKE (restarted at #{p['retake_of_later']})" if "retake_of_later" in p else ""
            lines.append(f"[{fmt_time(p['s'])}–{fmt_time(p['e'])}] #{p['i0']}{spk} {text}{flag}")
        (out / f"{f.stem}.md").write_text("\n".join(lines) + "\n")
        wav.unlink(missing_ok=True)
        print(f"    → {dst.relative_to(dst.parents[2])} ({len(words)} words)")


if __name__ == "__main__":
    main()
