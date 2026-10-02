import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
STATIC_UPLOADS = os.path.join(PROJECT_ROOT, "uploads")
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
                refs.append({
                    "id": spk,
                    "title": f"Reference Baseline ({spk})",
                    "duration": 60.0,
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

    # Prioritize user-provided transcript, fall back to baseline's transcript
    active_transcript = None
    if transcript and transcript.strip():
        active_transcript = transcript.strip()
    elif os.path.exists(ref_transcript_file):
        with open(ref_transcript_file, "r", encoding="utf-8") as f:
            active_transcript = f.read().strip()

    # Save uploaded audio file locally
    saved_filename = f"user_{audio.filename}"
    saved_audio_path = os.path.join(STATIC_UPLOADS, saved_filename)
    with open(saved_audio_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    # 1. Run real text-grounded alignment with the active transcript
    align_audio_file(saved_audio_path, reference_transcript=active_transcript, force_recompute=True)
    align_audio_file(ideal_wav, reference_transcript=active_transcript, force_recompute=False)

    # 2. Extract features and detect anomalies
    df_ideal = extract_features_per_word(ideal_wav)
    df_part = extract_features_per_word(saved_audio_path)

    regions = detect_anomalies(ideal_wav, saved_audio_path)

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
            return {"t": [], "f0": [], "rate": [], "pause": []}
        t = [round(float((s + e) / 2), 2) for s, e in zip(df["start"], df["end"])]
        f0 = [round(float(v), 2) if not np.isnan(v) else 0.0 for v in df["f0_hz_zscore"]]
        rate = [round(float(v), 2) for v in df["speech_rate"]]
        pause = [round(float(v), 2) for v in df["pause_before"]]
        return {"t": t, "f0": f0, "rate": rate, "pause": pause}

    return {
        "reference_id": reference_id,
        "audio_url": f"/static/uploads/{saved_filename}",
        "duration": round(part_dur, 2),
        "ground_truth_aligned": bool(active_transcript),
        "scores": scores,
        "regions": formatted_regions,
        "series": {
            "ref": to_series(df_ideal),
            "part": to_series(df_part)
        }
    }