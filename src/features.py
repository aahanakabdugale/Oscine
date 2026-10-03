import os
import json
import numpy as np
import pandas as pd
import librosa
from align import align_audio_file

_FEATURES_CACHE = {}


def extract_features_per_word(audio_path: str, alignment_json_path: str = None, force_recompute: bool = False) -> pd.DataFrame:
    """
    Extracts aligned word-level prosodic features:
    - Pitch (F0 median, std, semitone delta, z-score)
    - Pacing (speech rate in WPS)
    - Silence (preceding pause duration)
    - Volume / Energy (mean RMS energy & z-score)
    - Timbre (13 MFCC coefficients)
    """
    audio_mtime = os.path.getmtime(audio_path) if os.path.exists(audio_path) else 0.0
    cache_key = (os.path.abspath(audio_path), audio_mtime)
    if not force_recompute and cache_key in _FEATURES_CACHE:
        return _FEATURES_CACHE[cache_key].copy()

    feat_json_path = os.path.splitext(audio_path)[0] + ".features.json"
    if not force_recompute and os.path.exists(feat_json_path):
        try:
            cached_df = pd.read_json(feat_json_path)
            if not cached_df.empty:
                _FEATURES_CACHE[cache_key] = cached_df.copy()
                return cached_df
        except Exception:
            pass

    if alignment_json_path is None:
        aligned_path = os.path.splitext(audio_path)[0] + ".aligned.json"
        words_path = os.path.splitext(audio_path)[0] + "_words.json"
        if os.path.exists(aligned_path):
            alignment_json_path = aligned_path
        elif os.path.exists(words_path):
            alignment_json_path = words_path
        else:
            reference_transcript = None
            transcript_path = os.path.join(os.path.dirname(audio_path), "transcript.txt")
            if os.path.exists(transcript_path):
                with open(transcript_path, "r", encoding="utf-8") as tf:
                    reference_transcript = tf.read().strip()
            alignment_json_path = align_audio_file(
                audio_path,
                reference_transcript=reference_transcript,
                force_recompute=False
            )

    if not os.path.exists(alignment_json_path):
        return pd.DataFrame()

    with open(alignment_json_path, "r", encoding="utf-8") as f:
        align_data = json.load(f)

    words = align_data if isinstance(align_data, list) else align_data.get("words", [])
    if not words:
        return pd.DataFrame()

    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    # Cap duration to 60 seconds max for cloud stability
    if len(y) > 60 * sr:
        y = y[:60 * sr]
    hop_length = 512

    # 1. High-speed pitch extraction via YIN (runs in <0.2s instead of 90s on CPU)
    sr_pitch = 8000
    y_pitch = librosa.resample(y, orig_sr=sr, target_sr=sr_pitch)
    hop_pitch = int(hop_length * (sr_pitch / sr)) # 256 frames
    f0 = librosa.yin(
        y_pitch,
        fmin=65.0,
        fmax=400.0,
        sr=sr_pitch,
        hop_length=hop_pitch
    )
    f0_times = librosa.times_like(f0, sr=sr_pitch, hop_length=hop_pitch)
    voiced_flag = ((f0 > 66.0) & (f0 < 395.0) & ~np.isnan(f0)).astype(int)

    # 2. Continuous RMS energy
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    rms_times = librosa.times_like(rms, sr=sr, hop_length=hop_length)

    # 3. MFCC extraction (13 coefficients)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)
    mfcc_times = librosa.times_like(mfcc, sr=sr, hop_length=hop_length)

    # 4. Direct FFT-based Spectral Metrics (Vocal Clarity & Frequency Centroid)
    spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    spec_flat = librosa.feature.spectral_flatness(y=y, hop_length=hop_length)[0]

    # Compute global file-level normalization baselines
    valid_f0 = f0[voiced_flag > 0]
    valid_f0 = valid_f0[~np.isnan(valid_f0)]
    global_f0_mean = float(np.mean(valid_f0)) if len(valid_f0) > 0 else 150.0
    global_f0_std = float(np.std(valid_f0)) if len(valid_f0) > 0 else 25.0

    global_rms_mean = float(np.mean(rms)) if len(rms) > 0 else 0.05
    global_rms_std = float(np.std(rms)) if len(rms) > 0 else 0.02

    records = []
    prev_end = 0.0

    for idx, w in enumerate(words):
        w_start = float(w["start"])
        w_end = float(w["end"])
        w_dur = max(0.05, w_end - w_start)

        pause_before = max(0.0, w_start - prev_end)
        prev_end = w_end

        # Local speech rate: 3-word moving window
        win_start_idx = max(0, idx - 1)
        win_end_idx = min(len(words), idx + 2)
        span_dur = max(0.1, float(words[win_end_idx - 1]["end"]) - float(words[win_start_idx]["start"]))
        speech_rate = (win_end_idx - win_start_idx) / span_dur

        # Slice F0 in word interval
        f0_mask = (f0_times >= w_start) & (f0_times <= w_end) & (voiced_flag > 0)
        word_f0 = f0[f0_mask]
        word_f0 = word_f0[~np.isnan(word_f0)]
        f0_median = float(np.median(word_f0)) if len(word_f0) > 0 else global_f0_mean
        f0_zscore = (f0_median - global_f0_mean) / max(global_f0_std, 1e-4)

        # Slice RMS energy in word interval
        rms_mask = (rms_times >= w_start) & (rms_times <= w_end)
        word_rms = rms[rms_mask]
        rms_mean = float(np.mean(word_rms)) if len(word_rms) > 0 else global_rms_mean
        rms_zscore = (rms_mean - global_rms_mean) / max(global_rms_std, 1e-4)

        rec = {
            "word": w["word"],
            "start": round(w_start, 3),
            "end": round(w_end, 3),
            "duration": round(w_dur, 3),
            "pause_before": round(pause_before, 3),
            "speech_rate": round(speech_rate, 2),
            "f0_median_hz": round(f0_median, 1),
            "f0_hz_zscore": round(f0_zscore, 2),
            "rms_energy": round(rms_mean, 4),
            "rms_energy_zscore": round(rms_zscore, 2),
            "spectral_centroid_hz": round(float(np.mean(spec_cent[rms_mask])) if np.any(rms_mask) else 0.0, 1),
            "vocal_clarity_flatness": round(float(np.mean(spec_flat[rms_mask])) if np.any(rms_mask) else 0.0, 4),
        }

        # MFCC coefficients (use dedicated mfcc_mask — frame count may differ from rms)
        mfcc_mask = (mfcc_times >= w_start) & (mfcc_times <= w_end)
        for k in range(13):
            rec[f"mfcc_{k+1}"] = round(float(np.mean(mfcc[k, mfcc_mask])) if np.any(mfcc_mask) else 0.0, 3)

        records.append(rec)

    res_df = pd.DataFrame(records)
    _FEATURES_CACHE[cache_key] = res_df.copy()
    try:
        res_df.to_json(feat_json_path, orient="records", indent=2)
    except Exception:
        pass
    return res_df