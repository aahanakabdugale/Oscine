import os
import sys
import glob
import json
import pandas as pd

# Add current folder to sys.path so detect and explain resolve regardless of how python is called
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from detect import detect_anomalies
from explain import generate_causal_explanation, compute_rubric_scores

def calculate_iou(boxA, boxB):
    """Computes 1D temporal Intersection over Union between two intervals [start, end]."""
    tStart = max(boxA[0], boxB[0])
    tEnd = min(boxA[1], boxB[1])
    inter = max(0.0, tEnd - tStart)
    
    union = (boxA[1] - boxA[0]) + (boxB[1] - boxB[0]) - inter
    if union <= 0:
        return 0.0
    return inter / union

def run_evaluation():
    dataset_dir = "dataset"
    results = []

    speech_dirs = sorted(glob.glob(os.path.join(dataset_dir, "speech_*")))

    for s_dir in speech_dirs:
        speaker_id = os.path.basename(s_dir)
        ideal_wav = os.path.join(s_dir, "ideal.wav")
        labels_json = os.path.join(s_dir, "labels.json")

        if not os.path.exists(labels_json):
            continue

        with open(labels_json, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

        gt_dict = {item["file"]: item for item in gt_data["flaws"]}

        test_wavs = sorted(glob.glob(os.path.join(s_dir, "flawed_*.wav")))
        for test_wav in test_wavs:
            filename = os.path.basename(test_wav)
            if filename not in gt_dict:
                continue

            gt_meta = gt_dict[filename]
            gt_box = [gt_meta["t_start"], gt_meta["t_end"]]
            gt_type = gt_meta["flaw_type"]
            severity = gt_meta["severity"]

            # Run detection pipeline
            detected_regions = detect_anomalies(ideal_wav, test_wav)
            
            # Find highest matching IoU for the target flaw type
            best_iou = 0.0
            matched_region = None

            for reg in detected_regions:
                if reg["flaw_type"] == gt_type:
                    iou = calculate_iou([reg["t_start"], reg["t_end"]], gt_box)
                    if iou > best_iou:
                        best_iou = iou
                        matched_region = reg

            explanation = generate_causal_explanation(matched_region) if matched_region else "No anomaly detected."
            rubric = compute_rubric_scores(detected_regions)

            results.append({
                "speaker": speaker_id,
                "file": filename,
                "flaw_type": gt_type,
                "severity": severity,
                "gt_start": gt_box[0],
                "gt_end": gt_box[1],
                "det_start": round(matched_region["t_start"], 2) if matched_region else None,
                "det_end": round(matched_region["t_end"], 2) if matched_region else None,
                "iou": round(best_iou, 3),
                "overall_score": rubric["overall_score"],
                "explanation": explanation
            })
            print(f"[{speaker_id}] {filename:22s} | IoU: {best_iou:.3f} | Score: {rubric['overall_score']}")

    df_res = pd.DataFrame(results)
    df_res.to_csv("results.csv", index=False)
    print("\nSaved evaluation results to results.csv")

    # Generate Summary Table: Average IoU by flaw_type and severity
    summary = df_res.groupby(["flaw_type", "severity"])["iou"].agg(["mean", "count"]).reset_index()
    summary["mean"] = summary["mean"].round(3)
    print("\n========================================================")
    print("      AVERAGE IoU BENCHMARK BY FLAW & SEVERITY")
    print("========================================================")
    print(summary.to_string(index=False))

if __name__ == "__main__":
    run_evaluation()