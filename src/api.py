import os
import sys
import shutil
import tempfile
import wave
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from align import align_audio_file
from detect import detect_anomalies
from explain import generate_causal_explanation, compute_rubric_scores
from features import extract_features_per_word

app = FastAPI(title="Oscine Prosody Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")
STATIC_UPLOADS = os.path.join(tempfile.gettempdir(), "oscine_uploads")
os.makedirs(STATIC_UPLOADS, exist_ok=True)

app.mount("/static/uploads", StaticFiles(directory=STATIC_UPLOADS), name="uploads")
app.mount("/static/dataset", StaticFiles(directory=DATASET_DIR), name="dataset")


@app.get("/api/references")
def get_references():
    refs = []
    for spk in sorted(os.listdir(DATASET_DIR)):
        spk_dir = os.path.join(DATASET_DIR, spk)
        if os.path.isdir(spk_dir) and spk.startswith("speech_"):
            ideal_wav = os.path.join(spk_dir, "ideal.wav")
            trans_path = os.path.join(spk_dir, "transcript.txt")
            if os.path.exists(ideal_wav):
                transcript_text = ""
                if os.path.exists(trans_path):
                    with open(trans_path, "r", encoding="utf-8") as f:
                        transcript_text = f.read().strip()
                duration = 60.0
                try:
                    with wave.open(ideal_wav, "rb") as wf:
                        duration = round(wf.getnframes() / float(wf.getframerate()), 2)
                except Exception:
                    pass
                refs.append({
                    "id": spk,
                    "title": f"Reference Baseline ({spk})",
                    "duration": duration,
                    "transcript": transcript_text
                })
    return refs


@app.post("/api/analyze")
async def analyze_speech(
    reference_id: str = Form(...),
    audio: UploadFile = File(...),
    transcript: str = Form(None)
):
    ref_dir = os.path.join(DATASET_DIR, reference_id)
    ideal_wav = os.path.join(ref_dir, "ideal.wav")
    ref_transcript_file = os.path.join(ref_dir, "transcript.txt")

    if not os.path.exists(ideal_wav):
        raise HTTPException(status_code=404, detail=f"Reference baseline '{reference_id}' not found.")

    # Check if this is an existing benchmark preset in the dataset
    preset_wav = os.path.join(ref_dir, audio.filename)
    is_dataset_preset = os.path.exists(preset_wav)

    # Ground-truth transcript resolution
    baseline_ideal_transcript = None
    if os.path.exists(ref_transcript_file):
        with open(ref_transcript_file, "r", encoding="utf-8") as f:
            baseline_ideal_transcript = f.read().strip()

    active_transcript = None
    if transcript and transcript.strip():
        active_transcript = transcript.strip()
    elif is_dataset_preset or audio.filename.startswith("flawed_") or audio.filename.startswith("ideal_") or audio.filename == "ideal.wav":
        active_transcript = baseline_ideal_transcript

    # Determine audio location & stream URL
    if is_dataset_preset:
        audio_to_analyze = preset_wav
        audio_url = f"/static/dataset/{reference_id}/{audio.filename}"
    else:
        # Save to external temp folder (prevents Uvicorn watchfiles reload loops)
        saved_filename = f"user_{audio.filename}"
        saved_audio_path = os.path.join(STATIC_UPLOADS, saved_filename)
        with open(saved_audio_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        audio_to_analyze = saved_audio_path
        audio_url = f"/static/uploads/{saved_filename}"

    # 1. Run real text-grounded alignment (presets reuse their pre-computed alignment)
    align_audio_file(audio_to_analyze, reference_transcript=active_transcript, force_recompute=not is_dataset_preset)
    align_audio_file(ideal_wav, reference_transcript=baseline_ideal_transcript, force_recompute=False)

    # 2. Extract features and detect anomalies (ideal is instant via memory cache)
    df_ideal = extract_features_per_word(ideal_wav, force_recompute=False)
    df_part = extract_features_per_word(audio_to_analyze, force_recompute=not is_dataset_preset)

    regions = detect_anomalies(ideal_wav, audio_to_analyze, df_ideal=df_ideal, df_test=df_part)

    # Compute duration ratio
    ref_dur = float(df_ideal["end"].max()) if not df_ideal.empty else 60.0
    part_dur = float(df_part["end"].max()) if not df_part.empty else 60.0
    duration_ratio = part_dur / max(ref_dur, 1.0)

    # 3. Generate explanations & rubric scores
    formatted_regions = []
    for r in regions:
        explanation = generate_causal_explanation(r)
        formatted_regions.append({
            "dimension": r["flaw_type"],
            "start": round(float(r["t_start"]), 2),
            "end": round(float(r["t_end"]), 2),
            "peak_z": round(float(r["max_sigma"]), 2),
            "explanation": explanation
        })

    scores = compute_rubric_scores(regions, total_duration_sec=part_dur, duration_ratio=duration_ratio)

    # 4. Extract time series for synchronized charts
    def to_series(df):
        if df.empty:
            return {"t": [], "f0": [], "rate": [], "pause": [], "energy": [], "clarity": []}
        t = [round(float((s + e) / 2), 2) for s, e in zip(df["start"], df["end"])]
        f0 = [round(float(v), 2) if not np.isnan(v) else 0.0 for v in df["f0_hz_zscore"]]
        rate = [round(float(v), 2) for v in df["speech_rate"]]
        pause = [round(float(v), 2) for v in df["pause_before"]]
        energy = [round(float(v), 2) for v in df.get("rms_energy_zscore", [0.0] * len(df))]
        clarity = [round(float(v), 4) for v in df.get("vocal_clarity_flatness", [0.0] * len(df))]
        return {"t": t, "f0": f0, "rate": rate, "pause": pause, "energy": energy, "clarity": clarity}

    return {
        "reference_id": reference_id,
        "audio_url": audio_url,
        "duration": round(part_dur, 2),
        "ground_truth_aligned": bool(active_transcript),
        "scores": scores,
        "regions": formatted_regions,
        "series": {
            "ref": to_series(df_ideal),
            "part": to_series(df_part)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["src"])