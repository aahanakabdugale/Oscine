import json
import os
import sys

import pandas as pd
import soundfile as sf

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from detect import detect_anomalies
from explain import compute_rubric_scores

DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")
IOU_HIT_THRESHOLD = 0.25

TARGET_SCORE_BY_FLAW = {
    "errant_pause": "pauses_score",
    "rushed_delivery": "pacing_score",
    "monotone_pitch": "expressiveness_score",
    "volume_instability": "volume_score",
    "vocal_clarity_drift": "expressiveness_score",
}


def _merge_intervals(intervals):
    """Return the union of valid intervals, merging overlaps but not gaps."""
    merged = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def compute_interval_iou(pred_start, pred_end, gt_start, gt_end):
    """Compute temporal IoU between one prediction and one ground-truth interval."""
    if pred_end <= pred_start or gt_end <= gt_start:
        return 0.0

    intersection = max(0.0, min(pred_end, gt_end) - max(pred_start, gt_start))
    union = (pred_end - pred_start) + (gt_end - gt_start) - intersection
    return float(intersection / union) if union > 0 else 0.0


def compute_regions_iou(regions, flaw_type, gt_start, gt_end):
    """Compute IoU for the union of all detections matching the target flaw."""
    if gt_end <= gt_start:
        return 0.0

    intervals = _merge_intervals(
        [
            (float(region["t_start"]), float(region["t_end"]))
            for region in regions
            if region.get("flaw_type") == flaw_type
        ]
    )
    if not intervals:
        return 0.0

    predicted_duration = sum(end - start for start, end in intervals)
    intersection = sum(
        max(0.0, min(end, gt_end) - max(start, gt_start))
        for start, end in intervals
    )
    union = predicted_duration + (gt_end - gt_start) - intersection
    return float(intersection / union) if union > 0 else 0.0


def _normalize_labels(raw_labels):
    """Accept the current label list and the earlier object-with-flaws schema."""
    if isinstance(raw_labels, list):
        labels = raw_labels
    elif isinstance(raw_labels, dict) and isinstance(raw_labels.get("flaws"), list):
        labels = raw_labels["flaws"]
    elif isinstance(raw_labels, dict):
        labels = [value for value in raw_labels.values() if isinstance(value, dict)]
    else:
        raise ValueError("labels.json must contain a list or an object with a flaws list.")

    normalized = []
    for index, label in enumerate(labels):
        if not isinstance(label, dict):
            raise ValueError(f"Ground-truth label {index} must be a JSON object.")

        filename = label.get("filename", label.get("file"))
        flaw_type = label.get("flaw_type")
        severity = label.get("severity")
        start = label.get("start", label.get("t_start"))
        end = label.get("end", label.get("t_end"))
        if not filename or not flaw_type or not severity or start is None or end is None:
            raise ValueError(f"Ground-truth label {index} is missing required fields.")

        start, end = float(start), float(end)
        if end <= start:
            raise ValueError(
                f"Ground-truth interval for {filename} must have end > start."
            )

        normalized.append(
            {
                "filename": filename,
                "flaw_type": flaw_type,
                "severity": severity,
                "start": start,
                "end": end,
            }
        )
    return normalized


def _format_detections(regions, flaw_type):
    matching = [region for region in regions if region.get("flaw_type") == flaw_type]
    if matching:
        return ", ".join(
            f"{region['t_start']:.1f}-{region['t_end']:.1f}" for region in matching
        )
    if regions:
        first = regions[0]
        return f"wrong:{first['flaw_type']}:{first['t_start']:.1f}-{first['t_end']:.1f}"
    return "none"


def _strictly_descending(values):
    return (
        len(values) >= 2
        and all(value is not None for value in values)
        and all(values[index] > values[index + 1] for index in range(len(values) - 1))
    )


def evaluate_benchmark():
    print("========================================================")
    print("   RUNNING CALIBRATED CONTRASTIVE BENCHMARK EVALUATION  ")
    print("========================================================")

    speaker_dirs = sorted(
        name
        for name in os.listdir(DATASET_DIR)
        if name.startswith("speech_")
        and os.path.isdir(os.path.join(DATASET_DIR, name))
    )

    # ---------------------------------------------------------
    # 1. EVALUATE CLEAN CONTROL GROUP (CLIP-LEVEL FALSE POSITIVES)
    # ---------------------------------------------------------
    print("\n>>> 1. Testing Control Group (ideal vs ideal)...")
    control_clips = 0
    control_flagged_clips = 0
    control_false_alarm_regions = 0

    for speaker in speaker_dirs:
        ideal_wav = os.path.join(DATASET_DIR, speaker, "ideal.wav")
        if not os.path.exists(ideal_wav):
            print(f"  [SKIP] {speaker}: ideal.wav not found")
            continue

        control_clips += 1
        control_regions = detect_anomalies(ideal_wav, ideal_wav)
        duration = float(sf.info(ideal_wav).duration)
        control_scores = compute_rubric_scores(
            control_regions, total_duration_sec=duration
        )
        region_count = len(control_regions)
        control_false_alarm_regions += region_count
        control_flagged_clips += int(region_count > 0)
        print(
            f"  [{speaker}] Control Check: {region_count} false-alarm regions | "
            f"Score: {control_scores['overall_score']}"
        )

    if control_clips == 0:
        raise RuntimeError(f"No control recordings (ideal.wav) found under {DATASET_DIR}")

    fpr = 100.0 * control_flagged_clips / control_clips
    print(
        f"\n>> Control False Positive Rate (FPR): {fpr:.1f}% "
        f"({control_flagged_clips}/{control_clips} clips flagged; "
        f"{control_false_alarm_regions} false-alarm regions)"
    )

    # ---------------------------------------------------------
    # 2. EVALUATE FLAWED MATRIX
    # ---------------------------------------------------------
    print("\n>>> 2. Evaluating Flawed Speech Matrix...")
    print(
        f"{'speaker':<10} {'file':<26} {'type':<18} {'sev':<4} "
        f"{'gt_bounds':<15} | {'det':<32} | {'iou':<6} | "
        f"{'hit':<5} | {'score':<5}"
    )

    results = []
    missing_audio = 0

    for speaker in speaker_dirs:
        speaker_dir = os.path.join(DATASET_DIR, speaker)
        ideal_wav = os.path.join(speaker_dir, "ideal.wav")
        labels_path = os.path.join(speaker_dir, "labels.json")

        if not os.path.exists(ideal_wav):
            continue
        if not os.path.exists(labels_path):
            print(f"  [SKIP] {speaker}: labels.json not found")
            continue

        with open(labels_path, "r", encoding="utf-8") as label_file:
            labels = _normalize_labels(json.load(label_file))

        ideal_duration = float(sf.info(ideal_wav).duration)
        for label in labels:
            filename = label["filename"]
            test_wav = os.path.join(speaker_dir, filename)
            if not os.path.exists(test_wav):
                missing_audio += 1
                print(f"  [SKIP] {speaker}/{filename}: audio file not found")
                continue

            flaw_type = label["flaw_type"]
            gt_start = label["start"]
            gt_end = label["end"]
            severity = label["severity"]

            regions = detect_anomalies(ideal_wav, test_wav)
            iou = compute_regions_iou(regions, flaw_type, gt_start, gt_end)
            is_hit = iou >= IOU_HIT_THRESHOLD
            detected = _format_detections(regions, flaw_type)

            test_duration = float(sf.info(test_wav).duration)
            duration_ratio = test_duration / ideal_duration if ideal_duration > 0 else 1.0
            scores = compute_rubric_scores(
                regions,
                total_duration_sec=test_duration,
                duration_ratio=duration_ratio,
            )
            target_score_key = TARGET_SCORE_BY_FLAW.get(flaw_type)
            target_score = (
                scores[target_score_key] if target_score_key else scores["overall_score"]
            )

            gt_str = f"{gt_start:.1f}-{gt_end:.1f}"
            print(
                f"{speaker:<10} {filename:<26} {flaw_type:<18} {severity:<4} "
                f"{gt_str:<15} | {detected:<32} | {iou:<6.2f} | "
                f"{str(is_hit):<5} | {scores['overall_score']:.2f}"
            )

            results.append(
                {
                    "speaker": speaker,
                    "filename": filename,
                    "flaw_type": flaw_type,
                    "severity": severity,
                    "gt_start": gt_start,
                    "gt_end": gt_end,
                    "detected": detected,
                    "iou": round(iou, 3),
                    "hit": is_hit,
                    "score": scores["overall_score"],
                    "target_score_dimension": target_score_key or "overall_score",
                    "target_score": target_score,
                    "duration_sec": round(test_duration, 3),
                    "duration_ratio": round(duration_ratio, 4),
                    "detection_count": len(regions),
                    "matching_detection_count": sum(
                        region.get("flaw_type") == flaw_type for region in regions
                    ),
                }
            )

    if missing_audio:
        print(f"\n[WARNING] Skipped {missing_audio} labeled clips with missing audio.")

    df_results = pd.DataFrame(results)
    output_csv = os.path.join(PROJECT_ROOT, "results.csv")
    df_results.to_csv(output_csv, index=False)
    print(f"\nSaved all results to {output_csv}")

    if df_results.empty:
        print("[WARNING] No labeled flawed clips were evaluated; skipping summaries.")
        return df_results

    # ---------------------------------------------------------
    # 3. TEMPORAL DETECTION AND SCORE REPORTING
    # ---------------------------------------------------------
    print("\n========================================================")
    print(f"      TEMPORAL DETECTION GROUNDING (IoU >= {IOU_HIT_THRESHOLD:.2f})")
    print("========================================================")
    hit_summary = (
        df_results.groupby(["flaw_type", "severity"], observed=True)
        .agg(mean_iou=("iou", "mean"), hits=("hit", "sum"), total=("hit", "count"))
        .reset_index()
    )
    hit_summary["hit_rate_pct"] = 100.0 * hit_summary["hits"] / hit_summary["total"]
    print(hit_summary.to_string(index=False, float_format=lambda value: f"{value:.3f}"))

    total_hits = int(df_results["hit"].sum())
    total_clips = len(df_results)
    overall_hit_rate = 100.0 * total_hits / total_clips
    print(
        f"\n>> Overall Detection Hit Rate: {overall_hit_rate:.1f}% "
        f"({total_hits}/{total_clips} clips grounded with "
        f"IoU >= {IOU_HIT_THRESHOLD:.2f})"
    )

    print("\n========================================================")
    print("           RUBRIC SCORE MONOTONICITY GRADIENT           ")
    print("========================================================")
    severity_means = df_results.groupby("severity", observed=True)["score"].mean()
    overall_values = [10.0] + [
        float(severity_means[level]) if level in severity_means else None
        for level in ("L1", "L2", "L3")
    ]
    print("L0: 10.00 (Clean Control)")
    for level in ("L1", "L2", "L3"):
        if level in severity_means:
            print(f"{level}: {severity_means[level]:.2f}")
        else:
            print(f"{level}: N/A (no evaluated clips)")
    print(
        "\nStrictly monotonic across tiers (L0 > L1 > L2 > L3): "
        f"{_strictly_descending(overall_values)}"
    )

    print("\n--- Target-Dimension Score by Flaw and Severity (Each row should descend) ---")
    target_score_matrix = df_results.pivot_table(
        index="flaw_type",
        columns="severity",
        values="target_score",
        aggfunc="mean",
        observed=True,
    )
    ordered_levels = [level for level in ("L1", "L2", "L3") if level in target_score_matrix]
    if ordered_levels:
        print(target_score_matrix[ordered_levels].round(2).to_string())
    else:
        print("No severity levels available.")
    print("========================================================")
    return df_results


if __name__ == "__main__":
    evaluate_benchmark()
