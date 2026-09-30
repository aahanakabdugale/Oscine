import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import subprocess
import soundfile as sf
import librosa
import numpy as np
import noisereduce as nr
from faster_whisper import WhisperModel

print("Loading Whisper model...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

SPEECHES = [
    {
        "id": "speech_01",
        "name": "Michelle Obama",
        "raw_file": "data/raw/michelle_obama.mp3",
        "exact_start": 74.0,
        "exact_end": 136.0
    },
    {
        "id": "speech_02",
        "name": "Sudha Murty",
        "raw_file": "data/raw/sudha_murty.mp3",
        "exact_start": 10.0,
        "exact_end": 70.0
    },
    {
        "id": "speech_03",
        "name": "Emma Watson",
        "raw_file": "data/raw/emma_watson.mp3",
        "exact_start": 8.0,
        "exact_end": 68.0
    },
    {
        "id": "speech_04",
        "name": "Dr. Shashi Tharoor",
        "raw_file": "data/raw/tharoor.mp3",
        "exact_start": 21.0,
        "exact_end": 81.0
    },
    {
        "id": "speech_05",
        "name": "Lee Kuan Yew",
        "raw_file": "data/raw/lee_kuan_yew.mp3",
        "exact_start": 15.0,
        "exact_end": 75.0
    },
    {
        "id": "speech_06",
        "name": "Chimamanda Ngozi Adichie",
        "raw_file": "data/raw/chimamanda.mp3",
        "exact_start": 12.0,
        "exact_end": 72.0
    }
]

def clean_and_process(cfg):
    raw_path = cfg["raw_file"]
    speech_id = cfg["id"]
    out_dir = os.path.join("dataset", speech_id)
    os.makedirs(out_dir, exist_ok=True)

    final_wav = os.path.join(out_dir, "ideal.wav")
    out_txt = os.path.join(out_dir, "transcript.txt")
    temp_cut = os.path.join(out_dir, "temp_cut.wav")

    if not os.path.exists(raw_path):
        print(f"[SKIPPED] File not found: {raw_path}")
        return

    print(f"\n==========================================")
    print(f"Processing: {cfg['name']} ({speech_id})")
    print(f"==========================================")

    start = cfg["exact_start"]
    dur = cfg["exact_end"] - cfg["exact_start"]

    # 1. Precise FFmpeg cut with 50ms fade-in/out to prevent audio pops
    cut_cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-t", f"{dur:.3f}",
        "-i", raw_path,
        "-ar", "16000",
        "-ac", "1",
        "-af", f"afade=t=in:ss=0:d=0.05,afade=t=out:st={dur-0.05:.3f}:d=0.05",
        temp_cut
    ]
    subprocess.run(cut_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 2. Spectral noise suppression targeting background crowd noise & hall reverb
    y, sr = librosa.load(temp_cut, sr=16000, mono=True)
    y_clean = nr.reduce_noise(
        y=y,
        sr=sr,
        prop_decrease=0.92,
        stationary=False,
        n_std_thresh_stationary=1.5
    )
    sf.write(temp_cut, y_clean, sr)

    # 3. Loudness normalization to EBU R128 (-20 LUFS)
    norm_cmd = [
        "ffmpeg", "-y",
        "-i", temp_cut,
        "-ar", "16000",
        "-ac", "1",
        "-af", "loudnorm=I=-20:TP=-2",
        "-c:a", "pcm_s16le",
        final_wav
    ]
    subprocess.run(norm_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 4. Transcribe directly via in-memory NumPy float32 array (bypasses av.open entirely)
    final_audio, _ = librosa.load(final_wav, sr=16000, mono=True)
    segments, _ = whisper_model.transcribe(final_audio.astype(np.float32), language="en")
    transcript_text = " ".join([s.text.strip() for s in segments])

    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(transcript_text + "\n")

    if os.path.exists(temp_cut):
        os.remove(temp_cut)

    print(f"  [OK] Saved: {final_wav} ({dur:.2f}s)")
    print(f"  [OK] Saved: {out_txt}")

if __name__ == "__main__":
    for item in SPEECHES:
        clean_and_process(item)
    print("\nProcessing complete.")