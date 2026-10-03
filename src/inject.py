import os
import json
import numpy as np
import soundfile as sf
import librosa

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")

# Fixed anchor intervals per speaker (in reference timeline seconds)
FLAW_ANCHORS = {
    "errant_pause": (18.0, 18.0),       # Point insertion of silence
    "rushed_delivery": (25.0, 30.0),    # Target clause for acceleration
    "monotone_pitch": (35.0, 44.0),     # Target clause for dynamic flattening
}

# Strict Acoustic Severity Ladders
SEVERITY_CONFIG = {
    "errant_pause": {
        "L1": {"pause_sec": 1.2},   # Mild hesitation
        "L2": {"pause_sec": 2.2},   # Noticeable disruption
        "L3": {"pause_sec": 3.8},   # Severe rhetorical stall
    },
    "rushed_delivery": {
        # Speed rates tuned to keep phonetic boundaries intact for alignment
        "L1": {"rate": 1.30},  # ~30% faster
        "L2": {"rate": 1.55},  # ~55% faster
        "L3": {"rate": 1.80},  # ~80% faster (controlled ceiling)
    },
    "monotone_pitch": {
        # Fractional pitch modulation dampening (0.0 = completely flat)
        "L1": {"pitch_var_scale": 0.45},  # 55% reduction in modulation
        "L2": {"pitch_var_scale": 0.20},  # 80% reduction
        "L3": {"pitch_var_scale": 0.05},  # 95% reduction (pure robotic flatline)
    }
}


def inject_pause(y: np.ndarray, sr: int, insert_sec: float, pause_sec: float) -> np.ndarray:
    """Inserts a calibrated silent interval with gentle 15ms cosine crossfades to prevent clicks."""
    insert_sample = int(insert_sec * sr)
    silence_samples = int(pause_sec * sr)
    fade_len = int(0.015 * sr)

    part1 = y[:insert_sample].copy()
    part2 = y[insert_sample:].copy()

    # Apply brief fade out/in around the cut
    if len(part1) > fade_len:
        fade_out = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_len)))
        part1[-fade_len:] *= fade_out

    if len(part2) > fade_len:
        fade_in = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fade_len)))
        part2[:fade_len:] *= fade_in

    silence = np.zeros(silence_samples, dtype=y.dtype)
    return np.concatenate([part1, silence, part2])


def inject_rushed(y: np.ndarray, sr: int, start_sec: float, end_sec: float, rate: float) -> np.ndarray:
    """
    Accelerates the target interval using time-stretch WSOLA algorithm
    with cross-fading to preserve continuous phonetic articulation.
    """
    s_idx = int(start_sec * sr)
    e_idx = int(end_sec * sr)
    fade_len = int(0.02 * sr)

    prefix = y[:s_idx]
    target_segment = y[s_idx:e_idx]
    suffix = y[e_idx:]

    # Librosa time_stretch: rate > 1.0 speeds up audio (shortens duration)
    stretched = librosa.effects.time_stretch(target_segment, rate=rate)

    # Crossfade splice boundaries
    if len(prefix) > fade_len and len(stretched) > fade_len:
        fade_out = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_len)))
        fade_in = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fade_len)))
        prefix[-fade_len:] *= fade_out
        stretched[:fade_len] *= fade_in

    return np.concatenate([prefix, stretched, suffix])


def inject_monotone(y: np.ndarray, sr: int, start_sec: float, end_sec: float, var_scale: float) -> np.ndarray:
    """
    Compresses pitch variance toward the speaker's median F0 to simulate monotone delivery.
    Divides the target segment into N chunks, estimates each chunk's average F0,
    and shifts each chunk toward the global median by -(deviation * (1 - var_scale)).
    var_scale=0.45 -> 55% compression (L1), 0.20 -> 80% (L2), 0.05 -> 95% (L3/robotic flat).
    """
    s_idx = int(start_sec * sr)
    e_idx = int(end_sec * sr)
    fade_len = int(0.02 * sr)

    prefix = y[:s_idx]
    segment = y[s_idx:e_idx]
    suffix = y[e_idx:]

    try:
        hop_length = 512
        f0, voiced_flag, _ = librosa.pyin(
            segment,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sr,
            hop_length=hop_length
        )
        valid_f0 = f0[voiced_flag > 0]
        valid_f0 = valid_f0[np.isfinite(valid_f0) & (valid_f0 > 0)]

        if len(valid_f0) < 5:
            processed = segment.copy()
        else:
            median_f0 = float(np.median(valid_f0))
            f0_times = librosa.times_like(f0, sr=sr, hop_length=hop_length)

            # Split into N_CHUNKS and shift each toward the global median
            N_CHUNKS = 8
            chunk_len = len(segment) // N_CHUNKS
            chunks_out = []

            for ci in range(N_CHUNKS):
                cs = ci * chunk_len
                ce = cs + chunk_len if ci < N_CHUNKS - 1 else len(segment)
                chunk = segment[cs:ce]

                # Average voiced F0 within this chunk's time range
                chunk_mask = (
                    (f0_times >= cs / sr) & (f0_times < ce / sr)
                    & (voiced_flag > 0) & np.isfinite(f0) & (f0 > 0)
                )
                chunk_f0_vals = f0[chunk_mask]

                if len(chunk_f0_vals) > 0:
                    chunk_median = float(np.median(chunk_f0_vals))
                    # Semitone deviation of this chunk from global median
                    deviation = 12.0 * np.log2(chunk_median / median_f0)
                    # Pull toward global median proportional to (1 - var_scale)
                    n_steps = -deviation * (1.0 - var_scale)
                else:
                    n_steps = 0.0

                if abs(n_steps) > 0.1:
                    chunk_shifted = librosa.effects.pitch_shift(chunk, sr=sr, n_steps=n_steps)
                else:
                    chunk_shifted = chunk.copy()

                chunks_out.append(chunk_shifted)

            processed = np.concatenate(chunks_out).astype(segment.dtype)

    except Exception:
        processed = segment.copy()

    # Crossfade splice boundaries
    if len(prefix) > fade_len and len(processed) > fade_len:
        fade_out = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fade_len)))
        fade_in = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fade_len)))
        prefix[-fade_len:] *= fade_out
        processed[:fade_len] *= fade_in

    return np.concatenate([prefix, processed, suffix])


def synthesize_all_flaws():
    """Generates the full contrastive matrix: 6 speakers x 3 flaw types x 3 severities = 54 audio clips."""
    print("========================================================")
    print("       SYNTHESIZING CONTRASTIVE FLAW MATRIX (54 CLIPS)   ")
    print("========================================================")

    speaker_dirs = sorted([d for d in os.listdir(DATASET_DIR) if d.startswith("speech_")])
    total_generated = 0

    for spk in speaker_dirs:
        spk_path = os.path.join(DATASET_DIR, spk)
        ideal_wav = os.path.join(spk_path, "ideal.wav")
        if not os.path.exists(ideal_wav):
            continue

        y_ideal, sr = librosa.load(ideal_wav, sr=16000, mono=True)
        ideal_dur = len(y_ideal) / sr

        labels_records = []

        for flaw_type, anchor in FLAW_ANCHORS.items():
            s_anchor, e_anchor = anchor
            # Ensure anchor fits inside audio bounds
            s_anchor = min(s_anchor, ideal_dur - 5.0)
            e_anchor = min(e_anchor, ideal_dur - 1.0)

            for sev in ["L1", "L2", "L3"]:
                cfg = SEVERITY_CONFIG[flaw_type][sev]
                out_name = f"flawed_{flaw_type.split('_')[0] if 'pause' not in flaw_type else 'pause'}_{sev}.wav"
                out_path = os.path.join(spk_path, out_name)

                if flaw_type == "errant_pause":
                    pause_dur = cfg["pause_sec"]
                    y_mod = inject_pause(y_ideal, sr, insert_sec=s_anchor, pause_sec=pause_dur)
                    test_start = round(s_anchor, 2)
                    test_end = round(s_anchor + pause_dur, 2)

                elif flaw_type == "rushed_delivery":
                    rate = cfg["rate"]
                    y_mod = inject_rushed(y_ideal, sr, start_sec=s_anchor, end_sec=e_anchor, rate=rate)
                    orig_span = e_anchor - s_anchor
                    compressed_span = orig_span / rate
                    test_start = round(s_anchor, 2)
                    test_end = round(s_anchor + compressed_span, 2)

                elif flaw_type == "monotone_pitch":
                    var_scale = cfg["pitch_var_scale"]
                    y_mod = inject_monotone(y_ideal, sr, start_sec=s_anchor, end_sec=e_anchor, var_scale=var_scale)
                    test_start = round(s_anchor, 2)
                    test_end = round(e_anchor, 2)

                # Save 16-bit PCM WAV
                sf.write(out_path, y_mod, sr, subtype='PCM_16')
                test_dur = round(len(y_mod) / sr, 3)

                labels_records.append({
                    "speaker": spk,
                    "filename": out_name,
                    "flaw_type": flaw_type,
                    "severity": sev,
                    "start": test_start,
                    "end": test_end,
                    "ideal_timeline_start": round(s_anchor, 2),
                    "ideal_timeline_end": round(e_anchor, 2),
                    "test_duration": test_dur,
                    "ideal_duration": round(ideal_dur, 3)
                })
                total_generated += 1

        # Write labels.json for this speaker
        labels_json_path = os.path.join(spk_path, "labels.json")
        with open(labels_json_path, "w", encoding="utf-8") as f:
            json.dump(labels_records, f, indent=2)

        print(f"[{spk}] Generated 9 flawed variants + updated labels.json")

    # Update root dataset/labels.json with all records
    all_labels = []
    for spk in speaker_dirs:
        lp = os.path.join(DATASET_DIR, spk, "labels.json")
        if os.path.exists(lp):
            with open(lp, "r", encoding="utf-8") as f:
                all_labels.extend(json.load(f))

    root_labels = os.path.join(DATASET_DIR, "labels.json")
    with open(root_labels, "w", encoding="utf-8") as f:
        json.dump(all_labels, f, indent=2)

    print("--------------------------------------------------------")
    print(f"[OK] Completed synthesis of {total_generated} clips across {len(speaker_dirs)} speakers.")
    print(f"[OK] Synchronized all ground-truth records into: {root_labels}")
    print("========================================================")


if __name__ == "__main__":
    synthesize_all_flaws()