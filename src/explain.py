# src/explain.py
import numpy as np


# ----------------------------------------------------------------------
# 1. CAUSAL EXPLANATIONS
# ----------------------------------------------------------------------
def generate_causal_explanation(region):
    """
    Transforms a detected acoustic anomaly region into a structured, human-readable
    causal explanation with exact mathematical deltas and pedagogical coaching advice.
    """
    flaw = region["flaw_type"]
    t_s = float(region["t_start"])
    t_e = float(region["t_end"])
    sigma = float(region["max_sigma"])
    dur = round(t_e - t_s, 2)
    details = region.get("details", [])
    words_list = region.get("words", [])
    sample_words = " ".join(f"'{w}'" for w in words_list[:4]) if words_list else "spoken tokens"

    if flaw == "rushed_delivery":
        ref_rates = [d.get("ref_rate", 0) for d in details if d.get("ref_rate", 0) > 0]
        tgt_rates = [d.get("tgt_rate", 0) for d in details if d.get("tgt_rate", 0) > 0]
        mean_ref = float(np.mean(ref_rates)) if ref_rates else 2.5
        mean_tgt = float(np.mean(tgt_rates)) if tgt_rates else 3.8
        ratio = round(mean_tgt / max(mean_ref, 1e-4), 2)
        compression_pct = round((1.0 - 1.0 / max(ratio, 1.0)) * 100, 1)
        return (
            f"[{t_s:.2f}s – {t_e:.2f}s] Syllabic Acceleration ({ratio:.2f}x tempo, +{sigma:.2f}σ): "
            f"Speech rate surged to {mean_tgt:.2f} wps vs {mean_ref:.2f} wps baseline "
            f"({compression_pct:.1f}% time compression) across {sample_words}. "
            f"Causal impact: Rapid tempo erodes phonetic clarity and prevents rhetorical points from landing. "
            f"Coaching: Lengthen stressed vowel durations and insert micro-pauses before key conceptual shifts."
        )

    if flaw == "errant_pause":
        pause_vals = [d.get("pause_dur", 0.0) for d in details if "pause_dur" in d]
        max_pause = max(pause_vals) if pause_vals else dur
        deltas = [d.get("silence_delta", max_pause) for d in details if "silence_delta" in d]
        silence_delta = max(deltas) if deltas else max_pause
        ref_pauses = [d.get("ref_pause", 0.0) for d in details if "ref_pause" in d]
        ref_pause = min(ref_pauses) if ref_pauses else 0.0
        return (
            f"[{t_s:.2f}s – {t_e:.2f}s] Errant Pause Hesitation ({max_pause:.2f}s silence, +{sigma:.2f}σ): "
            f"Dead air exceeded expected baseline pause by +{silence_delta:.2f}s (reference baseline: {ref_pause:.2f}s) "
            f"around {sample_words}. Causal impact: Disrupts rhetorical flow and signals memory lapse or hesitation. "
            f"Coaching: Maintain steady diaphragmatic breath support and bridge phrases smoothly."
        )

    if flaw == "monotone_pitch":
        collapses = [d.get("collapse_pct", 70.0) for d in details if "collapse_pct" in d]
        collapse_pct = max(collapses) if collapses else 70.0
        tgt_vars = [d.get("tgt_pitch_var", 0.2) for d in details if "tgt_pitch_var" in d]
        ref_vars = [d.get("ref_pitch_var", 1.0) for d in details if "ref_pitch_var" in d]
        tgt_var = float(np.mean(tgt_vars)) if tgt_vars else 0.2
        ref_var = float(np.mean(ref_vars)) if ref_vars else 1.0
        return (
            f"[{t_s:.2f}s – {t_e:.2f}s] Monotone Pitch Flattening ({collapse_pct:.1f}% inflection collapse, +{sigma:.2f}σ): "
            f"F₀ pitch variability compressed to {tgt_var:.2f} semitones vs {ref_var:.2f} semitones baseline "
            f"over a {dur:.2f}s window across {sample_words}. "
            f"Causal impact: A flatline acoustic contour robs the performance of emotional dynamism. "
            f"Coaching: Consciously modulate vocal pitch upward on key nouns and descend on concluding assertions."
        )

    if flaw == "volume_instability":
        rms_deltas = [d.get("rms_delta", sigma) for d in details if "rms_delta" in d]
        rms_delta = max(rms_deltas) if rms_deltas else sigma
        tgt_zs = [d.get("tgt_rms_z", 0.0) for d in details if "tgt_rms_z" in d]
        ref_zs = [d.get("ref_rms_z", 0.0) for d in details if "ref_rms_z" in d]
        tgt_z = float(np.mean(tgt_zs)) if tgt_zs else 0.0
        ref_z = float(np.mean(ref_zs)) if ref_zs else 0.0
        return (
            f"[{t_s:.2f}s – {t_e:.2f}s] Dynamic Volume Instability (|Δz| = {rms_delta:.2f}σ, +{sigma:.2f}σ): "
            f"Energy dynamics drifted (participant: {tgt_z:+.2f}σ vs reference: {ref_z:+.2f}σ) across {sample_words}. "
            f"Causal impact: Erratic loudness fluctuations undermine vocal projection and listener comfort. "
            f"Coaching: Anchor diaphragm engagement to ensure steady acoustic power without fading at sentence tails."
        )

    if flaw == "vocal_clarity_drift":
        drifts = [d.get("clarity_drift", 0.0) for d in details if "clarity_drift" in d]
        max_drift = max(drifts) if drifts else 0.40
        return (
            f"[{t_s:.2f}s – {t_e:.2f}s] Vocal Clarity / Timbre Drift (MFCC cosine dist: {max_drift:.3f}, +{sigma:.2f}σ): "
            f"Spectral timbre drifted from reference footprint across {sample_words}, signaling breathiness or muffle. "
            f"Causal impact: Reduced harmonic sharpness dampens phonemic clarity in competitive debate/oratory. "
            f"Coaching: Project sound into the forward facial mask and keep consistent microphone distance."
        )

    return f"[{t_s:.2f}s – {t_e:.2f}s] Acoustic deviation (+{sigma:.2f}σ) detected across {sample_words}."


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