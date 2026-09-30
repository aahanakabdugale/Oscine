import os
import json
import librosa
import soundfile as sf
import numpy as np

# ---------------------------------------------------------
# Flaw Synthesis Functions
# ---------------------------------------------------------

def inject_errant_pause(y, sr, t_insert_sec, silence_duration_sec):
    """
    Inserts dead air / hesitation silence at a specified timestamp.
    Shifts all downstream audio and timestamps forward.
    """
    insert_sample = int(t_insert_sec * sr)
    silence_len = int(silence_duration_sec * sr)
    
    # 5ms micro crossfade to eliminate edge clicks
    fade_len = int(0.005 * sr)
    silence_block = np.zeros(silence_len, dtype=np.float32)
    
    y_before = y[:insert_sample].copy()
    y_after = y[insert_sample:].copy()
    
    if len(y_before) > fade_len:
        y_before[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)
    if len(y_after) > fade_len:
        y_after[:fade_len] *= np.linspace(0.0, 1.0, fade_len)
        
    y_flawed = np.concatenate([y_before, silence_block, y_after])
    return y_flawed, silence_duration_sec


def inject_rushed_delivery(y, sr, t_start_sec, window_dur_sec, rate_multiplier):
    """
    Time-stretches an isolated window without modifying pitch.
    e.g., rate=1.5 causes 50% faster delivery (rushed cadence).
    """
    start_sample = int(t_start_sec * sr)
    end_sample = int((t_start_sec + window_dur_sec) * sr)
    
    y_head = y[:start_sample]
    y_segment = y[start_sample:end_sample]
    y_tail = y[end_sample:]
    
    # Time-stretch using phase vocoder (maintains vocal formants)
    y_stretched = librosa.effects.time_stretch(y_segment, rate=rate_multiplier)
    
    # Shift delta calculation for ground-truth labeling
    new_segment_dur = len(y_stretched) / sr
    time_shift = new_segment_dur - window_dur_sec
    
    y_flawed = np.concatenate([y_head, y_stretched, y_tail])
    return y_flawed, t_start_sec, t_start_sec + new_segment_dur


def inject_monotone(y, sr, t_start_sec, window_dur_sec, compression_ratio):
    """
    Simulates monotone by extracting the segment, flattening vocal pitch modulation,
    and clamping intonation inflection using harmonic pitch-clamping.
    """
    start_sample = int(t_start_sec * sr)
    end_sample = int((t_start_sec + window_dur_sec) * sr)
    
    y_flawed = y.copy()
    y_segment = y[start_sample:end_sample]
    
    # 1. Pitch shift down to kill high inflection, then mix to eliminate vibrato
    # L1: mild flattening (-1 semitone inflection suppression)
    # L2: clear monotone robotic suppression (-2.5 semitones)
    # L3: severe robotic flatline (-4 semitones)
    shift_steps = -4.0 * (1.0 - compression_ratio)
    y_shifted = librosa.effects.pitch_shift(y_segment, sr=sr, n_steps=shift_steps)
    
    # Combine original and shifted with heavy center weight to flatten contour
    y_flattened = (0.3 * y_segment) + (0.7 * y_shifted)
    
    # Smooth boundary crossfades (20ms) to prevent clicks
    fade_len = int(0.020 * sr)
    if len(y_segment) > 2 * fade_len:
        y_flattened[:fade_len] = (
            y_segment[:fade_len] * np.linspace(1, 0, fade_len) +
            y_flattened[:fade_len] * np.linspace(0, 1, fade_len)
        )
        y_flattened[-fade_len:] = (
            y_flattened[-fade_len:] * np.linspace(1, 0, fade_len) +
            y_segment[-fade_len:] * np.linspace(0, 1, fade_len)
        )
        
    y_flawed[start_sample:end_sample] = y_flattened
    return y_flawed


# ---------------------------------------------------------
# Generation Matrix Orchestrator
# ---------------------------------------------------------

FLAW_SPECS = [
    # Errant Pauses: inserted mid-sentence at t=18.0s
    {"type": "pause", "level": "L1", "param": 1.2, "t_start": 18.0},  # 1.2s dead air
    {"type": "pause", "level": "L2", "param": 2.5, "t_start": 18.0},  # 2.5s awkward pause
    {"type": "pause", "level": "L3", "param": 4.0, "t_start": 18.0},  # 4.0s severe pause breakdown
    
    # Rushed Speech: 6-second window compressed
    {"type": "rushed", "level": "L1", "param": 1.25, "t_start": 25.0, "dur": 6.0},  # 25% faster
    {"type": "rushed", "level": "L2", "param": 1.50, "t_start": 25.0, "dur": 6.0},  # 50% faster
    {"type": "rushed", "level": "L3", "param": 1.85, "t_start": 25.0, "dur": 6.0},  # 85% panic cadence
    
    # Monotone Delivery: 8-second window flattened
    {"type": "monotone", "level": "L1", "param": 0.65, "t_start": 35.0, "dur": 8.0}, # Slight flatline
    {"type": "monotone", "level": "L2", "param": 0.40, "t_start": 35.0, "dur": 8.0}, # Noticeable robotic pitch
    {"type": "monotone", "level": "L3", "param": 0.15, "t_start": 35.0, "dur": 8.0}  # Complete loss of prosody
]

def generate_flaws_for_speaker(speech_id):
    speech_dir = os.path.join("dataset", speech_id)
    ideal_wav = os.path.join(speech_dir, "ideal.wav")
    
    if not os.path.exists(ideal_wav):
        print(f"Skipping {speech_id}: ideal.wav not found.")
        return

    print(f"\n[Injecting Flaws] -> {speech_id}")
    y, sr = librosa.load(ideal_wav, sr=16000, mono=True)
    labels = {
        "speaker_id": speech_id,
        "base_file": "ideal.wav",
        "sample_rate": sr,
        "flaws": []
    }

    for spec in FLAW_SPECS:
        flaw_type = spec["type"]
        level = spec["level"]
        out_filename = f"flawed_{flaw_type}_{level}.wav"
        out_path = os.path.join(speech_dir, out_filename)
        
        if flaw_type == "pause":
            y_flawed, pause_len = inject_errant_pause(y, sr, spec["t_start"], spec["param"])
            ground_truth = {
                "file": out_filename,
                "flaw_type": "errant_pause",
                "severity": level,
                "t_start": spec["t_start"],
                "t_end": round(spec["t_start"] + pause_len, 3),
                "duration_delta": round(pause_len, 3)
            }
            
        elif flaw_type == "rushed":
            y_flawed, t_start, t_end = inject_rushed_delivery(y, sr, spec["t_start"], spec["dur"], spec["param"])
            ground_truth = {
                "file": out_filename,
                "flaw_type": "rushed_delivery",
                "severity": level,
                "t_start": round(t_start, 3),
                "t_end": round(t_end, 3),
                "speed_multiplier": spec["param"]
            }
            
        elif flaw_type == "monotone":
            y_flawed = inject_monotone(y, sr, spec["t_start"], spec["dur"], spec["param"])
            ground_truth = {
                "file": out_filename,
                "flaw_type": "monotone_pitch",
                "severity": level,
                "t_start": spec["t_start"],
                "t_end": spec["t_start"] + spec["dur"],
                "compression_ratio": spec["param"]
            }
            
        sf.write(out_path, y_flawed, sr)
        labels["flaws"].append(ground_truth)
        print(f"  + Generated {out_filename} ({level})")

    labels_path = os.path.join(speech_dir, "labels.json")
    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2)
    print(f"  -> Ground truth saved to {labels_path}")


if __name__ == "__main__":
    for i in range(1, 7):
        generate_flaws_for_speaker(f"speech_{i:02d}")
    print("\nAll synthetic flaw variants generated successfully.")