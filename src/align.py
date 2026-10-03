import os
import json
import re
import difflib
import librosa
from faster_whisper import WhisperModel

_MODEL = None


def get_whisper_model():
    global _MODEL
    if _MODEL is None:
        model_size = os.getenv("WHISPER_MODEL", "tiny")
        _MODEL = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=2)
    return _MODEL


def tokenize_text(text: str):
    """Normalizes and tokenizes text into lowercase alphanumeric words."""
    cleaned = re.sub(r"[^\w\s]", "", text).lower()
    return [w for w in cleaned.split() if w]


def align_tokens_to_transcript(whisper_words: list, transcript_tokens: list):
    """
    Performs dynamic-programming sequence alignment (Levenshtein matching)
    between Whisper word emissions and the ground-truth transcript tokens.
    Maps accurate temporal boundaries onto reference transcript words.
    """
    if not transcript_tokens:
        return whisper_words

    w_words = [w["word"] for w in whisper_words]
    matcher = difflib.SequenceMatcher(None, w_words, transcript_tokens)

    aligned_results = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for wi, tj in zip(range(i1, i2), range(j1, j2)):
                item = whisper_words[wi].copy()
                item["word"] = transcript_tokens[tj]
                item["aligned_to_transcript"] = True
                aligned_results.append(item)
        elif tag == "replace":
            # Matched phonetically or variant spelling
            w_slice = whisper_words[i1:i2]
            t_slice = transcript_tokens[j1:j2]
            if w_slice and t_slice:
                t_start = w_slice[0]["start"]
                t_end = w_slice[-1]["end"]
                step = (t_end - t_start) / max(len(t_slice), 1)
                for k, t_word in enumerate(t_slice):
                    aligned_results.append({
                        "word": t_word,
                        "start": round(float(t_start + (k * step)), 3),
                        "end": round(float(t_start + ((k + 1) * step)), 3),
                        "probability": 0.85,
                        "aligned_to_transcript": True
                    })
        elif tag == "delete":
            # Whisper recognized extra words not present in reference transcript
            continue
        elif tag == "insert":
            # Reference words skipped in audio (impute minimal anchor)
            anchor_t = aligned_results[-1]["end"] if aligned_results else 0.0
            for t_word in transcript_tokens[j1:j2]:
                aligned_results.append({
                    "word": t_word,
                    "start": round(float(anchor_t), 3),
                    "end": round(float(anchor_t + 0.1), 3),
                    "probability": 0.20,
                    "aligned_to_transcript": False,
                    "omitted_in_speech": True
                })
                anchor_t += 0.1

    return aligned_results if aligned_results else whisper_words


def align_audio_file(audio_path: str, reference_transcript: str = None, force_recompute: bool = False) -> str:
    """
    Runs word-level forced alignment.
    If reference_transcript is provided, it constrains Whisper's transcription
    and grounds emitted boundaries to the exact transcript tokens.
    """
    json_path = os.path.splitext(audio_path)[0] + ".aligned.json"
    if os.path.exists(json_path) and not force_recompute:
        # If cache exists, verify if ground truth alignment was requested
        with open(json_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
            if not reference_transcript or cache.get("ground_truth_guided"):
                return json_path

    model = get_whisper_model()
    y, sr = librosa.load(audio_path, sr=16000, mono=True)

    # Prompt guidance to bias ASR toward expected lexicon
    prompt = reference_transcript[:400] if reference_transcript else None
    segments, _ = model.transcribe(
        y,
        word_timestamps=True,
        beam_size=1,
        initial_prompt=prompt
    )

    whisper_words = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                cleaned = re.sub(r"[^\w\s]", "", w.word).strip().lower()
                if cleaned:
                    whisper_words.append({
                        "word": cleaned,
                        "start": round(float(w.start), 3),
                        "end": round(float(w.end), 3),
                        "probability": round(float(w.probability), 3)
                    })

    # Ground against reference transcript tokens if supplied
    transcript_tokens = tokenize_text(reference_transcript) if reference_transcript else []
    final_words = align_tokens_to_transcript(whisper_words, transcript_tokens)

    output_data = {
        "audio_file": os.path.basename(audio_path),
        "ground_truth_guided": bool(transcript_tokens),
        "total_words": len(final_words),
        "words": final_words
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    return json_path