import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from features import extract_features_per_word

DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")

def precompute_all():
    print("=" * 60)
    print("PRE-COMPUTING ACOUSTIC FEATURES FOR CLOUD DEPLOYMENT")
    print("=" * 60)
    
    total = 0
    skipped = 0
    computed = 0
    
    for spk in sorted(os.listdir(DATASET_DIR)):
        spk_dir = os.path.join(DATASET_DIR, spk)
        if not (os.path.isdir(spk_dir) and spk.startswith("speech_")):
            continue
            
        print(f"\nProcessing {spk}...")
        for fname in sorted(os.listdir(spk_dir)):
            if not fname.endswith(".wav"):
                continue
                
            total += 1
            wav_path = os.path.join(spk_dir, fname)
            feat_json = os.path.splitext(wav_path)[0] + ".features.json"
            
            if os.path.exists(feat_json) and os.path.getsize(feat_json) > 100:
                print(f"  [ALREADY CACHED] {fname}")
                skipped += 1
                continue
                
            print(f"  [EXTRACTING] {fname}...", end="", flush=True)
            df = extract_features_per_word(wav_path, force_recompute=True)
            if not df.empty:
                print(f" OK ({len(df)} words)")
                computed += 1
            else:
                print(" FAILED")

    print("\n" + "=" * 60)
    print(f"COMPLETED: {computed} computed, {skipped} already cached, total {total} clips.")
    print("=" * 60)

if __name__ == "__main__":
    precompute_all()
