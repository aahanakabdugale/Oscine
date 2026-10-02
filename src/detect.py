import os
import sys
from difflib import SequenceMatcher

import numpy as np
import pandas as pd
import librosa

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from features import extract_features_per_word


def cosine_distance(vec_a, vec_b):
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.clip(1.0 - (np.dot(vec_a, vec_b) / (norm_a * norm_b)), 0.0, 2.0))


def compute_rms_energy(audio_path: str):
    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    hop_length = 512
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    times = librosa.times_like(rms, sr=sr, hop_length=hop_length)
    return times, rms


def _silence_intervals(audio_path, minimum_duration=0.45):
    times, rms = compute_rms_energy(audio_path)
    times = np.asarray(times, dtype=float)
    rms = np.asarray(rms, dtype=float)
    if not len(rms):
        return []

    threshold = max(1e-4, float(np.percentile(rms, 75)) * 0.01)
    quiet = rms <= threshold
    frame_step = float(times[1] - times[0]) if len(times) > 1 else 0.032
    intervals = []
    start = None
    for index, is_quiet in enumerate(quiet):
        if is_quiet and start is None:
            start = index
        elif not is_quiet and start is not None:
            interval_start = max(0.0, float(times[start]) - frame_step / 2)
            interval_end = float(times[index - 1]) + frame_step / 2
            if interval_end - interval_start >= minimum_duration:
                intervals.append((interval_start, interval_end))
            start = None

    if start is not None:
        interval_start = max(0.0, float(times[start]) - frame_step / 2)
        interval_end = float(times[-1]) + frame_step / 2
        if interval_end - interval_start >= minimum_duration:
            intervals.append((interval_start, interval_end))
    return intervals


def _normalize_word(word):
    return "".join(character for character in str(word).lower() if character.isalnum())


def _align_reference_words(reference_words, test_words):
    """Map test words to reference positions using matching transcript tokens."""
    reference = [_normalize_word(word) for word in reference_words]
    test = [_normalize_word(word) for word in test_words]
    if not reference or not test:
        return np.zeros(len(test), dtype=int), np.zeros(len(test), dtype=bool)

    positions = np.full(len(test), np.nan)
    exact_matches = np.zeros(len(test), dtype=bool)
    matcher = SequenceMatcher(None, reference, test, autojunk=False)
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            test_index = block.b + offset
            positions[test_index] = block.a + offset
            exact_matches[test_index] = True

    matched_indices = np.flatnonzero(exact_matches)
    if len(matched_indices):
        positions = np.interp(
            np.arange(len(test)),
            matched_indices,
            positions[matched_indices],
        )
    else:
        positions = np.linspace(0, len(reference) - 1, len(test))

    return np.clip(np.rint(positions), 0, len(reference) - 1).astype(int), exact_matches


def _pitch_semitones(f0_values, reference_median):
    """Express F0 as semitones relative to the reference speaker's median pitch."""
    values = np.asarray(f0_values, dtype=float)
    valid = np.isfinite(values) & (values > 0)
    if not valid.any() or not np.isfinite(reference_median) or reference_median <= 0:
        return np.zeros(len(values), dtype=float)

    semitones = np.full(len(values), np.nan, dtype=float)
    semitones[valid] = 12.0 * np.log2(values[valid] / reference_median)
    valid_indices = np.flatnonzero(valid)
    return np.interp(np.arange(len(values)), valid_indices, semitones[valid])


def _merge_records_by_type(records, merge_gap_sec):
    """Merge overlapping or nearby detections independently for each flaw type."""
    merged = []
    flaw_types = dict.fromkeys(record["flaw_type"] for record in records)
    for flaw_type in flaw_types:
        typed_records = sorted(
            (record for record in records if record["flaw_type"] == flaw_type),
            key=lambda record: record["start"],
        )
        regions = []
        for record in typed_records:
            if regions and record["start"] - regions[-1]["t_end"] <= merge_gap_sec:
                region = regions[-1]
                region["t_end"] = max(region["t_end"], record["end"])
                region["max_sigma"] = max(region["max_sigma"], record["sigma_dev"])
                region["words"].append(record["word"])
                region["details"].append(record)
                continue

            regions.append(
                {
                    "flaw_type": flaw_type,
                    "t_start": record["start"],
                    "t_end": record["end"],
                    "max_sigma": record["sigma_dev"],
                    "words": [record["word"]],
                    "details": [record],
                }
            )
        merged.extend(regions)

    return sorted(merged, key=lambda region: region["t_start"])


def detect_anomalies(ideal_wav, test_wav, merge_gap_sec=0.2):
    """
    Evaluates contrastive acoustic deviations against the reference speaker baseline.
    """
    df_ideal = extract_features_per_word(ideal_wav)
    df_test = extract_features_per_word(test_wav)

    if df_ideal.empty or df_test.empty:
        return []

    df_ideal = df_ideal.reset_index(drop=True)
    df_test = df_test.reset_index(drop=True)
    ref_indices, exact_matches = _align_reference_words(
        df_ideal["word"].tolist(), df_test["word"].tolist()
    )
    ref = df_ideal.iloc[ref_indices].reset_index(drop=True)
    flagged_records = []
    n_test = len(df_test)
    test_centers = (df_test["start"].to_numpy(float) + df_test["end"].to_numpy(float)) / 2
    ref_centers = (
        df_ideal["start"].to_numpy(float) + df_ideal["end"].to_numpy(float)
    ) / 2
    valid_anchors = (
        exact_matches
        & ((df_test["end"] - df_test["start"]).to_numpy(float) <= 2.0)
        & ((df_ideal["end"] - df_ideal["start"]).to_numpy(float)[ref_indices] <= 2.0)
    )
    if valid_anchors.sum() >= 2:
        timeline_test = test_centers[valid_anchors]
        timeline_ref = ref_centers[ref_indices[valid_anchors]]
    else:
        timeline_test = np.array([], dtype=float)
        timeline_ref = np.array([], dtype=float)

    reference_silences = _silence_intervals(ideal_wav)
    for silence_start, silence_end in _silence_intervals(test_wav):
        if len(timeline_test) >= 2:
            expected_start = float(np.interp(silence_start, timeline_test, timeline_ref))
            expected_end = float(np.interp(silence_end, timeline_test, timeline_ref))
            if expected_end < expected_start:
                expected_start, expected_end = expected_end, expected_start
            expected_duration = expected_end - expected_start
            reference_silence_overlap = sum(
                max(0.0, min(expected_end, ref_end) - max(expected_start, ref_start))
                for ref_start, ref_end in reference_silences
            )
            if expected_duration > 0 and reference_silence_overlap / expected_duration >= 0.5:
                continue
        else:
            reference_silence_overlap = 0.0

        context_index = int(np.argmin(np.abs(test_centers - (silence_start + silence_end) / 2)))
        context_word = df_test["word"].iloc[context_index]
        silence_delta = max(0.0, silence_end - silence_start - reference_silence_overlap)
        flagged_records.append(
            {
                "flaw_type": "errant_pause",
                "start": float(silence_start),
                "end": float(silence_end),
                "sigma_dev": round(silence_delta * 2.0, 2),
                "word": context_word,
                "tgt_rate": float(df_test["speech_rate"].iloc[context_index]),
                "ref_rate": float(ref["speech_rate"].iloc[context_index]),
                "pause_dur": round(silence_end - silence_start, 3),
            }
        )

    ideal_f0_column = "f0_hz" if "f0_hz" in df_ideal else "f0_median_hz"
    test_f0_column = "f0_hz" if "f0_hz" in df_test else "f0_median_hz"
    ideal_f0 = (
        pd.to_numeric(df_ideal[ideal_f0_column], errors="coerce").to_numpy(float)
        if ideal_f0_column in df_ideal
        else np.full(len(df_ideal), np.nan)
    )
    valid_ideal_f0 = ideal_f0[np.isfinite(ideal_f0) & (ideal_f0 > 0)]
    reference_median = float(np.median(valid_ideal_f0)) if len(valid_ideal_f0) else np.nan
    ideal_pitch = _pitch_semitones(ideal_f0, reference_median)
    test_pitch = _pitch_semitones(
        pd.to_numeric(df_test[test_f0_column], errors="coerce").to_numpy(float)
        if test_f0_column in df_test
        else np.full(len(df_test), np.nan),
        reference_median,
    )
    pitch_window = 5
    ideal_pitch_std = (
        pd.Series(ideal_pitch)
        .rolling(window=pitch_window, min_periods=3, center=True)
        .std()
        .fillna(0.0)
        .to_numpy()
    )
    test_pitch_std = (
        pd.Series(test_pitch)
        .rolling(window=pitch_window, min_periods=3, center=True)
        .std()
        .fillna(0.0)
        .to_numpy()
    )

    test_durations = (df_test["end"] - df_test["start"]).clip(lower=0.02)
    reference_durations = (
        (ref["end"] - ref["start"]).clip(lower=0.02).where(exact_matches)
    )
    window_size = 3
    test_duration_windows = test_durations.rolling(
        window=window_size, min_periods=2, center=True
    ).sum()
    reference_duration_windows = reference_durations.rolling(
        window=window_size, min_periods=2, center=True
    ).sum()
    matched_word_windows = (
        pd.Series(exact_matches.astype(int))
        .rolling(window=window_size, min_periods=2, center=True)
        .sum()
    )

    for i, w_tgt in df_test.iterrows():
        if not exact_matches[i]:
            continue
        w_ref = ref.iloc[i]

        # -------------------------------------------------------------
        # 2. RUSHED DELIVERY
        # Compare durations of the same matched words in a local window.
        # -------------------------------------------------------------
        ref_window = reference_duration_windows.iloc[i]
        test_window = test_duration_windows.iloc[i]
        matched_window = matched_word_windows.iloc[i]
        rate_ratio = (
            float(ref_window / test_window)
            if pd.notna(ref_window)
            and pd.notna(test_window)
            and test_window > 0
            and matched_window >= 2
            else 1.0
        )
        if rate_ratio >= 1.15:
            window_word_count = int(matched_window)
            ref_rate = window_word_count / max(float(ref_window), 1e-6)
            tgt_rate = window_word_count / max(float(test_window), 1e-6)
            flagged_records.append({
                "flaw_type": "rushed_delivery",
                "start": float(w_tgt["start"]),
                "end": float(w_tgt["end"]),
                "sigma_dev": round(rate_ratio - 1.0, 3),
                "word": w_tgt["word"],
                "tgt_rate": tgt_rate,
                "ref_rate": ref_rate,
                "pause_dur": float(w_tgt["pause_before"]),
            })

        # -------------------------------------------------------------
        # 3. MONOTONE PITCH
        # Compare local pitch variation with the aligned reference context.
        # -------------------------------------------------------------
        ref_pitch_var = float(ideal_pitch_std[ref_indices[i]])
        tgt_pitch_var = float(test_pitch_std[i])
        if ref_pitch_var >= 0.8 and tgt_pitch_var <= 0.65 * ref_pitch_var:
            collapse_ratio = 1.0 - tgt_pitch_var / max(ref_pitch_var, 1e-6)
            sigma_val = max(1.0, collapse_ratio * 4.0)
            flagged_records.append({
                "flaw_type": "monotone_pitch",
                "start": float(w_tgt["start"]),
                "end": float(w_tgt["end"]),
                "sigma_dev": round(sigma_val, 2),
                "word": w_tgt["word"],
                "tgt_rate": float(w_tgt["speech_rate"]),
                "ref_rate": float(w_ref["speech_rate"]),
                "pause_dur": float(w_tgt["pause_before"]),
            })

        # -------------------------------------------------------------
        # 4. VOLUME INSTABILITY
        # -------------------------------------------------------------
        rms_delta = abs(w_tgt.get("rms_energy_zscore", 0.0) - w_ref.get("rms_energy_zscore", 0.0))
        if rms_delta >= 2.2 and w_tgt["pause_before"] < 0.5:
            flagged_records.append({
                "flaw_type": "volume_instability",
                "start": float(w_tgt["start"]),
                "end": float(w_tgt["end"]),
                "sigma_dev": round(float(rms_delta), 2),
                "word": w_tgt["word"],
                "tgt_rate": float(w_tgt["speech_rate"]),
                "ref_rate": float(w_ref["speech_rate"]),
                "pause_dur": float(w_tgt["pause_before"]),
            })

    return _merge_records_by_type(flagged_records, merge_gap_sec)