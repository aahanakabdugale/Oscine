import os
import sys

# Ensure src/ and repo root are in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from features import extract_features_per_word

def detect_anomalies(ideal_wav, test_wav, z_threshold=1.3, merge_gap_sec=1.5):
    df_ideal = extract_features_per_word(ideal_wav)
    df_test = extract_features_per_word(test_wav)

    if df_ideal.empty or df_test.empty:
        return []

    # Calculate ideal baseline statistics across the whole speech
    mean_rate = df_ideal["speech_rate"].mean()
    std_rate = max(df_ideal["speech_rate"].std(), 0.1)
    
    mean_pause = df_ideal["pause_before"].mean()
    std_pause = max(df_ideal["pause_before"].std(), 0.1)

    flagged_records = []

    for i, w in df_test.iterrows():
        # 1. Pause Flaw: check if pause gap before word is an outlier
        pause_sigma = (w["pause_before"] - mean_pause) / std_pause
        if w["pause_before"] >= 1.0 and pause_sigma >= 1.8:
            # The flaw happens during the silence BEFORE the word
            flagged_records.append({
                "flaw_type": "errant_pause",
                "start": max(0.0, float(w["start"] - w["pause_before"])),
                "end": float(w["start"]),
                "sigma_dev": round(float(pause_sigma), 2),
                "word": w["word"],
                "tgt_rate": float(w["speech_rate"]),
                "ref_rate": float(mean_rate),
                "pause_dur": float(w["pause_before"])
            })

        # 2. Rushed Flaw: local speech rate spike
        rate_sigma = (w["speech_rate"] - mean_rate) / std_rate
        if rate_sigma >= z_threshold or w["speech_rate_zscore"] >= 1.5:
            flagged_records.append({
                "flaw_type": "rushed_delivery",
                "start": float(w["start"]),
                "end": float(w["end"]),
                "sigma_dev": round(float(rate_sigma), 2),
                "word": w["word"],
                "tgt_rate": float(w["speech_rate"]),
                "ref_rate": float(mean_rate),
                "pause_dur": float(w["pause_before"])
            })

        # 3. Monotone Flaw: flatline pitch variation (low std) or significant pitch clamp
        if abs(w["f0_hz_zscore"]) >= 1.8:
            flagged_records.append({
                "flaw_type": "monotone_pitch",
                "start": float(w["start"]),
                "end": float(w["end"]),
                "sigma_dev": round(abs(float(w["f0_hz_zscore"])), 2),
                "word": w["word"],
                "tgt_rate": float(w["speech_rate"]),
                "ref_rate": float(mean_rate),
                "pause_dur": float(w["pause_before"])
            })

    if not flagged_records:
        return []

    # Merge consecutive or overlapping detections of the same flaw type
    flagged_records.sort(key=lambda x: x["start"])
    merged = []
    curr = flagged_records[0].copy()
    curr_region = {
        "flaw_type": curr["flaw_type"],
        "t_start": curr["start"],
        "t_end": curr["end"],
        "max_sigma": curr["sigma_dev"],
        "words": [curr["word"]],
        "details": [curr]
    }

    for nxt in flagged_records[1:]:
        gap = nxt["start"] - curr_region["t_end"]
        if (nxt["flaw_type"] == curr_region["flaw_type"]) and (gap <= merge_gap_sec):
            curr_region["t_end"] = max(curr_region["t_end"], nxt["end"])
            curr_region["max_sigma"] = max(curr_region["max_sigma"], nxt["sigma_dev"])
            curr_region["words"].append(nxt["word"])
            curr_region["details"].append(nxt)
        else:
            merged.append(curr_region)
            curr_region = {
                "flaw_type": nxt["flaw_type"],
                "t_start": nxt["start"],
                "t_end": nxt["end"],
                "max_sigma": nxt["sigma_dev"],
                "words": [nxt["word"]],
                "details": [nxt]
            }
    merged.append(curr_region)
    return merged

if __name__ == "__main__":
    ideal = "dataset/speech_01/ideal.wav"
    test = "dataset/speech_01/flawed_rushed_L3.wav"
    regions = detect_anomalies(ideal, test)
    print(f"Detected {len(regions)} anomaly regions in {test}:")
    for r in regions:
        print(f"  [{r['flaw_type']}] {r['t_start']:.2f}s - {r['t_end']:.2f}s | Max Dev: {r['max_sigma']} sigma | Words: {' '.join(r['words'][:5])}...")