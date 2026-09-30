import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import glob
import json
import librosa
import numpy as np
from faster_whisper import WhisperModel

print("Loading Whisper model for word-level temporal alignment...")
# Running "base" on CPU with int8 quantization for fast execution
model = WhisperModel("base", device="cpu", compute_type="int8")

def align_audio_file(audio_path):
    out_json = audio_path.replace(".wav", "_words.json")
    
    # Skip if already generated to save time on restarts
    if os.path.exists(out_json):
        print(f"  [EXISTS] {os.path.basename(out_json)}")
        return

    # Load audio into memory to avoid any PyAV / av.open issues
    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    
    # Transcribe with word-level timestamps enabled
    segments, _ = model.transcribe(
        y.astype(np.float32),
        word_timestamps=True,
        language="en"
    )
    
    word_records = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                cleaned_word = w.word.strip()
                if cleaned_word:
                    word_records.append({
                        "word": cleaned_word,
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "probability": round(w.probability, 3)
                    })

    # Save to disk
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(word_records, f, indent=2)

    print(f"  [OK] Aligned: {os.path.basename(audio_path)} -> {len(word_records)} words")

def run_alignment_pipeline():
    dataset_dir = "dataset"
    speech_dirs = sorted(glob.glob(os.path.join(dataset_dir, "speech_*")))
    
    if not speech_dirs:
        print("No speech directories found under dataset/")
        return

    for s_dir in speech_dirs:
        speech_id = os.path.basename(s_dir)
        print(f"\n==========================================")
        print(f"Aligning speech corpus: {speech_id}")
        print(f"==========================================")
        
        # Gather all .wav files in this speaker folder (ideal + all 9 flaws)
        wav_files = sorted(glob.glob(os.path.join(s_dir, "*.wav")))
        for wav_path in wav_files:
            align_audio_file(wav_path)

if __name__ == "__main__":
    run_alignment_pipeline()
    print("\nTask 1 complete: all word timestamps written to *_words.json.")