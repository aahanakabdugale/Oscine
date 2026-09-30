import os
import json
import librosa
import numpy as np
import pandas as pd

def extract_features_per_word(wav_path, words_json_path=None):
    """
    Extracts acoustic DSP features aligned per word:
      1. Pitch (F0) using librosa.pyin (fundamental frequency)
      2. Energy (RMS)
      3. Pause duration before the word
      4. Local Speech Rate (words per second in a local 3-second context)
      5. MFCCs (13 coefficients averaged over word duration)
      6. Z-score normalized features for speaker-agnostic comparison
    """
    if words_json_path is None:
        words_json_path = wav_path.replace(".wav", "_words.json")

    if not os.path.exists(words_json_path):
        raise FileNotFoundError(f"Missing words alignment JSON: {words_json_path}. Run src/align.py first.")

    with open(words_json_path, "r", encoding="utf-8") as f:
        words = json.load(f)

    if not words:
        return pd.DataFrame()

    # 1. Load Audio
    y, sr = librosa.load(wav_path, sr=16000, mono=True)
    hop_length = 512

    # 2. Extract Frame-Level Pitch (F0) via Probabilistic YIN
    # Human speech fundamental frequency typically spans 65 Hz (deep male) to 400 Hz (high female)
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=librosa.note_to_hz('C2'),  # ~65 Hz
        fmax=librosa.note_to_hz('G5'),  # ~392 Hz
        sr=sr,
        hop_length=hop_length
    )
    # Convert frame indices to time
    f0_times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop_length)

    # 3. Extract Frame-Level Energy (RMS)
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    # 4. Extract Frame-Level MFCCs (13 coefficients)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)

    rows = []
    prev_end = 0.0

    for idx, w in enumerate(words):
        w_text = w["word"]
        w_start = w["start"]
        w_end = w["end"]
        w_dur = max(w_end - w_start, 0.01)

        # A. Pause duration before current word (gap between previous word end & this start)
        pause_before = max(0.0, w_start - prev_end)
        prev_end = w_end

        # B. Slice frames corresponding to the word duration
        f0_mask = (f0_times >= w_start) & (f0_times <= w_end)
        rms_mask = (rms_times >= w_start) & (rms_times <= w_end)
        
        # Word F0: median of voiced frames (ignoring unvoiced NaNs)
        f0_word_frames = f0[f0_mask]
        f0_voiced = f0_word_frames[~np.isnan(f0_word_frames)]
        f0_val = float(np.median(f0_voiced)) if len(f0_voiced) > 0 else np.nan

        # Word RMS Energy: mean power across word
        rms_word_frames = rms[rms_mask]
        rms_val = float(np.mean(rms_word_frames)) if len(rms_word_frames) > 0 else 0.0

        # Word MFCCs: average vector across word frames
        if np.any(f0_mask):
            mfcc_val = np.mean(mfcc[:, f0_mask], axis=1)
        else:
            mfcc_val = np.zeros(13)

        # C. Local Speech Rate (words per second in a rolling 3-second window)
        win_start = max(0.0, w_start - 1.5)
        win_end = w_start + 1.5
        words_in_win = sum(1 for other_w in words if (other_w["start"] >= win_start and other_w["end"] <= win_end))
        speech_rate = words_in_win / (win_end - win_start)

        row = {
            "word": w_text,
            "start": w_start,
            "end": w_end,
            "duration": round(w_dur, 3),
            "pause_before": round(pause_before, 3),
            "speech_rate": round(speech_rate, 2),
            "f0_hz": round(f0_val, 2) if not np.isnan(f0_val) else np.nan,
            "rms_energy": round(rms_val, 4),
        }
        
        for m_i in range(13):
            row[f"mfcc_{m_i+1}"] = round(float(mfcc_val[m_i]), 4)

        rows.append(row)

    df = pd.DataFrame(rows)

    # 5. Apply Z-Score Normalization per file (Speaker-Agnostic Transformation)
    # Allows comparing high-pitch vs low-pitch, fast vs slow speakers directly
    for col in ["f0_hz", "rms_energy", "speech_rate", "pause_before"]:
        valid_series = df[col].dropna()
        std_val = valid_series.std()
        mean_val = valid_series.mean()
        
        # Guard against zero division
        if std_val > 1e-6:
            df[f"{col}_zscore"] = (df[col] - mean_val) / std_val
        else:
            df[f"{col}_zscore"] = 0.0

    return df

if __name__ == "__main__":
    flawed_wav = "dataset/speech_01/flawed_pause_L3.wav"
    print(f"Extracting features for {flawed_wav}...")
    df = extract_features_per_word(flawed_wav)

    # 1. Filter rows where an unnatural pause occurs (e.g., > 1.0 second)
    suspicious_pauses = df[df["pause_before"] > 1.0]

    print("\n--- Detected Significant Pauses ---")
    print(suspicious_pauses[["word", "start", "duration", "pause_before", "speech_rate"]])

    # 2. Check the context: 2 words before and after the big pause
    if not suspicious_pauses.empty:
        pause_idx = suspicious_pauses.index[0]
        context_slice = df.iloc[max(0, pause_idx - 2) : min(len(df), pause_idx + 3)]
        print("\n--- Word Context Around the Injected Pause ---")
        print(context_slice[["word", "start", "end", "pause_before"]])