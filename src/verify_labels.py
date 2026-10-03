import os
import json
import librosa

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")


def verify_and_calibrate_labels():
    if not os.path.exists(DATASET_DIR):
        print(f"Error: Could not find {DATASET_DIR}")
        return

    print("========================================================")
    print("        AUDITING & CALIBRATING DATASET LABELS          ")
    print("========================================================")

    all_consolidated_records = []
    total_calibrated = 0

    speaker_dirs = sorted([d for d in os.listdir(DATASET_DIR) if d.startswith("speech_")])

    for spk in speaker_dirs:
        spk_path = os.path.join(DATASET_DIR, spk)
        labels_file = os.path.join(spk_path, "labels.json")
        ideal_path = os.path.join(spk_path, "ideal.wav")

        if not os.path.exists(labels_file) or not os.path.exists(ideal_path):
            continue

        ideal_dur = round(float(librosa.get_duration(path=ideal_path)), 3)

        with open(labels_file, "r", encoding="utf-8") as f:
            raw_content = json.load(f)

        # Normalize content to a list of (key, dict_item)
        was_dict = isinstance(raw_content, dict)
        items_to_process = []
        if was_dict:
            for k, v in raw_content.items():
                if isinstance(v, dict):
                    item = v.copy()
                    if "filename" not in item:
                        item["filename"] = k if k.endswith(".wav") else f"{k}.wav"
                    items_to_process.append((k, item))
                elif isinstance(v, list):
                    for sub_item in v:
                        items_to_process.append((None, sub_item))
        elif isinstance(raw_content, list):
            for sub_item in raw_content:
                items_to_process.append((None, sub_item))

        updated_dict = {}
        updated_list = []

        for key, item in items_to_process:
            filename = item.get("filename")
            flaw_type = item.get("flaw_type")
            audio_path = os.path.join(spk_path, filename) if filename else None

            if not audio_path or not os.path.exists(audio_path):
                if was_dict and key is not None:
                    updated_dict[key] = item
                else:
                    updated_list.append(item)
                continue

            test_dur = round(float(librosa.get_duration(path=audio_path)), 3)
            raw_start = float(item.get("start", 0.0))
            raw_end = float(item.get("end", 0.0))

            calibrated_start = raw_start
            calibrated_end = raw_end

            if flaw_type == "errant_pause":
                added_silence = max(0.4, test_dur - ideal_dur)
                calibrated_start = round(raw_start, 2)
                calibrated_end = round(raw_start + added_silence, 2)

            elif flaw_type == "rushed_delivery":
                ideal_s = float(item.get("ideal_timeline_start", raw_start))
                ideal_e = float(item.get("ideal_timeline_end", raw_end))
                if ideal_e <= ideal_s:
                    ideal_e = ideal_s + 5.0
                time_compression = max(0.0, ideal_dur - test_dur)
                compressed_span = (ideal_e - ideal_s) - time_compression
                calibrated_start = round(ideal_s, 2)
                calibrated_end = round(ideal_s + max(1.5, compressed_span), 2)

            elif flaw_type == "monotone_pitch":
                calibrated_start = round(raw_start, 2)
                calibrated_end = round(min(raw_end, test_dur), 2)

            updated_item = item.copy()
            updated_item["speaker"] = spk
            updated_item["test_timeline_start"] = calibrated_start
            updated_item["test_timeline_end"] = calibrated_end
            updated_item["ideal_timeline_start"] = float(item.get("ideal_timeline_start", raw_start))
            updated_item["ideal_timeline_end"] = float(item.get("ideal_timeline_end", raw_end))
            updated_item["start"] = calibrated_start
            updated_item["end"] = calibrated_end
            updated_item["test_duration"] = test_dur
            updated_item["ideal_duration"] = ideal_dur

            if was_dict and key is not None:
                updated_dict[key] = updated_item
            else:
                updated_list.append(updated_item)

            all_consolidated_records.append(updated_item)
            total_calibrated += 1

        # Save preserving the original schema structure
        with open(labels_file, "w", encoding="utf-8") as f:
            if was_dict:
                json.dump(updated_dict, f, indent=2)
            else:
                json.dump(updated_list, f, indent=2)

        print(f"[{spk}] Calibrated labels successfully -> {labels_file}")

    # Write consolidated labels list to dataset/labels.json
    root_labels_path = os.path.join(DATASET_DIR, "labels.json")
    with open(root_labels_path, "w", encoding="utf-8") as f:
        json.dump(all_consolidated_records, f, indent=2)

    print("--------------------------------------------------------")
    print(f"[OK] Audited and calibrated {total_calibrated} labels across {len(speaker_dirs)} speakers.")
    print(f"[OK] Saved unified dataset ground-truth to: {root_labels_path}")
    print("========================================================")


if __name__ == "__main__":
    verify_and_calibrate_labels()