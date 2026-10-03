# src/explain.py
import numpy as np


# ----------------------------------------------------------------------
# 1. CAUSAL EXPLANATIONS
# ----------------------------------------------------------------------
def generate_causal_explanation(region):
    """
    Transforms a detected acoustic anomaly region into a template sentence
    populated with exact numbers.
    """
    flaw = region["flaw_type"]
    t_s = region["t_start"]
    t_e = region["t_end"]
    sigma = region["max_sigma"]
    dur = round(t_e - t_s, 2)
    details = region.get("details", [])
    sample_words = " ".join(f"'{w}'" for w in region.get("words", [])[:4])

    if flaw == "rushed_delivery":
        ref_rates = [d["ref_rate"] for d in details if d.get("ref_rate", 0) > 0]
        tgt_rates = [d["tgt_rate"] for d in details if d.get("tgt_rate", 0) > 0]
        mean_ref = float(np.mean(ref_rates)) if ref_rates else 1.0
        mean_tgt = float(np.mean(tgt_rates)) if tgt_rates else 1.0
        ratio = round(mean_tgt / max(mean_ref, 1e-4), 2)
        return (f"{t_s:.2f}s - {t_e:.2f}s: Pacing accelerated to {ratio}x baseline "
                f"(+{sigma} sigma). Syllabic compression detected across {sample_words}. "
                f"Recommend easing tempo before transitions.")

    if flaw == "errant_pause":
        pause_vals = [d["pause_dur"] for d in details if "pause_dur" in d]
        max_pause = max(pause_vals) if pause_vals else dur
        return (f"{t_s:.2f}s - {t_e:.2f}s: Errant hesitation of {max_pause:.2f}s "
                f"(+{sigma} sigma). Dead air exceeded expected baseline pause gap before "
                f"{sample_words}. Recommend continuous breath support.")

    if flaw == "monotone_pitch":
        return (f"{t_s:.2f}s - {t_e:.2f}s: Pitch inflection flattened "
                f"(+{sigma} sigma deviation). Acoustic contour showed compressed dynamic "
                f"range over a {dur}s window around {sample_words}.")

    if flaw == "volume_instability":
        return (f"{t_s:.2f}s - {t_e:.2f}s: Energy deviation of {sigma} sigma detected. "
                f"Unstable dynamic volume across {sample_words}.")

    if flaw == "vocal_clarity_drift":
        drifts = [d.get("clarity_drift", 0.0) for d in details]
        max_drift = max(drifts) if drifts else 0.0
        return (f"{t_s:.2f}s - {t_e:.2f}s: Vocal clarity/timbre drift of {max_drift:.2f} "
                f"detected across {sample_words} (MFCC spectral distance exceeded "
                f"threshold). Ensure consistent microphone distance and resonant vocal "
                f"placement.")

    return f"{t_s:.2f}s - {t_e:.2f}s: Acoustic deviation (+{sigma} sigma) detected."


# ----------------------------------------------------------------------
# 2. RUBRIC SCORING
# ----------------------------------------------------------------------


def compute_rubric_scores(regions: list, total_duration_sec: float = 60.0, duration_ratio: float = 1.0) -> dict:
    """
    Computes rubric scores out of 10.0 with dynamic volume instability deduction.
    """
    if not regions and abs(1.0 - duration_ratio) < 0.05:
        return {
            "overall_score": 10.0,
            "pacing_score": 10.0,
            "pauses_score": 10.0,
            "expressiveness_score": 10.0,
            "volume_score": 10.0,
        }

    dim_max_impact = {
        "errant_pause": 0.0,
        "rushed_delivery": 0.0,
        "monotone_pitch": 0.0,
        "volume_instability": 0.0,
        "vocal_clarity_drift": 0.0,
    }

    clip_duration = max(float(total_duration_sec), 1.0)
    for reg in regions:
        flaw = reg.get("flaw_type")
        if flaw in dim_max_impact:
            dur = max(0.4, reg.get("t_end", 0.0) - reg.get("t_start", 0.0))
            sigma = reg.get("max_sigma", 1.0)
            if flaw == "rushed_delivery":
                impact = max(0.0, float(sigma)) * (dur / clip_duration) ** 0.5
            else:
                impact = ((sigma / 1.8) ** 1.4) * (dur ** 0.5)
            if impact > dim_max_impact[flaw]:
                dim_max_impact[flaw] = impact

    compression_penalty = max(0.0, (1.0 - duration_ratio) * 15.0) if duration_ratio < 0.99 else 0.0

    pause_pen = min(dim_max_impact["errant_pause"] * 0.95, 6.0)
    pace_pen = (
        7.5 * (1.0 - float(np.exp(-dim_max_impact["rushed_delivery"] / 0.20)))
        + compression_penalty
    )
    pitch_pen = min(dim_max_impact["monotone_pitch"] * 0.85, 6.0)
    vol_pen = min(dim_max_impact["volume_instability"] * 0.90, 5.0)

    pauses_score = max(1.0, min(10.0, round(10.0 - pause_pen, 1)))
    pacing_score = max(1.0, min(10.0, round(10.0 - pace_pen, 1)))
    expressiveness_score = max(1.0, min(10.0, round(10.0 - pitch_pen, 1)))
    volume_score = max(1.0, min(10.0, round(10.0 - vol_pen, 1)))

    overall = round(
        float(0.35 * pacing_score + 0.35 * pauses_score + 0.20 * expressiveness_score + 0.10 * volume_score),
        2
    )

    return {
        "overall_score": overall,
        "pacing_score": pacing_score,
        "pauses_score": pauses_score,
        "expressiveness_score": expressiveness_score,
        "volume_score": volume_score,
    }