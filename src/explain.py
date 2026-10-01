import numpy as np

def generate_causal_explanation(region):
    """
    Transforms detected acoustic anomalies into template sentences populated with exact numbers.
    """
    flaw = region["flaw_type"]
    t_s = region["t_start"]
    t_e = region["t_end"]
    sigma = region["max_sigma"]
    dur = round(t_e - t_s, 2)
    sample_words = ' '.join(f"'{w}'" for w in region.get("words", [])[:4])

    if flaw == "rushed_delivery":
        ref_rates = [d["ref_rate"] for d in region.get("details", []) if d.get("ref_rate", 0) > 0]
        tgt_rates = [d["tgt_rate"] for d in region.get("details", [])]
        mean_ref = np.mean(ref_rates) if ref_rates else 1.0
        mean_tgt = np.mean(tgt_rates) if tgt_rates else 1.0
        ratio = round(mean_tgt / max(mean_ref, 1e-4), 2)
        return (f"{t_s:.2f}s - {t_e:.2f}s: Pacing accelerated to {ratio}x baseline (+{sigma} sigma). "
                f"Syllabic compression detected across {sample_words}. Recommend easing tempo before transitions.")

    elif flaw == "errant_pause":
        pause_vals = [d["pause_dur"] for d in region.get("details", []) if "pause_dur" in d]
        max_pause = max(pause_vals) if pause_vals else dur
        return (f"{t_s:.2f}s - {t_e:.2f}s: Errant hesitation of {max_pause:.2f}s (+{sigma} sigma). "
                f"Dead air exceeded expected baseline pause gap before {sample_words}. Recommend continuous breath support.")

    elif flaw == "monotone_pitch":
        return (f"{t_s:.2f}s - {t_e:.2f}s: Pitch inflection flattened (+{sigma} sigma deviation). "
                f"Acoustic contour showed compressed dynamic range over a {dur}s window around {sample_words}.")

    elif flaw == "volume_instability":
        return (f"{t_s:.2f}s - {t_e:.2f}s: Energy deviation of {sigma} sigma detected. "
                f"Unstable dynamic volume across {sample_words}.")

    return f"{t_s:.2f}s - {t_e:.2f}s: Acoustic deviation (+{sigma} sigma) detected."

def compute_rubric_scores(regions, total_duration_sec=60.0):
    """
    Deterministic Rubric scoring from 0.0 to 10.0 per dimension.
    Score = max(0.0, 10.0 - penalties)
    """
    penalties = {
        "pacing": 0.0,
        "pauses": 0.0,
        "volume": 0.0,
        "expressiveness": 0.0
    }

    for r in regions:
        region_dur = r["t_end"] - r["t_start"]
        dur_weight = (region_dur / max(total_duration_sec, 1.0)) * 10.0
        severity_mult = min(r["max_sigma"] / 2.0, 2.5)

        flaw = r["flaw_type"]
        if flaw == "rushed_delivery":
            penalties["pacing"] += dur_weight * severity_mult * 2.0
        elif flaw == "errant_pause":
            penalties["pauses"] += dur_weight * severity_mult * 2.5
        elif flaw == "monotone_pitch":
            penalties["expressiveness"] += dur_weight * severity_mult * 2.0
        elif flaw == "volume_instability":
            penalties["volume"] += dur_weight * severity_mult * 2.0

    scores = {
        "pacing_score": round(max(0.0, 10.0 - penalties["pacing"]), 2),
        "pauses_score": round(max(0.0, 10.0 - penalties["pauses"]), 2),
        "expressiveness_score": round(max(0.0, 10.0 - penalties["expressiveness"]), 2),
        "volume_score": round(max(0.0, 10.0 - penalties["volume"]), 2),
    }
    scores["overall_score"] = round(float(np.mean(list(scores.values()))), 2)
    return scores