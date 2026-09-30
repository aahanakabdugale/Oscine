import os
import matplotlib.pyplot as plt
from features import extract_features_per_word

def plot_ideal_vs_flawed(speaker_id="speech_01", flaw_name="flawed_rushed_L3"):
    speech_dir = os.path.join("dataset", speaker_id)
    ideal_wav = os.path.join(speech_dir, "ideal.wav")
    flawed_wav = os.path.join(speech_dir, f"{flaw_name}.wav")
    
    print(f"Extracting features for {ideal_wav}...")
    df_ideal = extract_features_per_word(ideal_wav)
    
    print(f"Extracting features for {flawed_wav}...")
    df_flawed = extract_features_per_word(flawed_wav)

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=False)
    fig.suptitle(f"Acoustic Contrast: {speaker_id} (Ideal vs. {flaw_name})", fontsize=14, fontweight="bold")

    # 1. Pitch Contour (F0 Z-Score)
    axes[0].plot(df_ideal["start"], df_ideal["f0_hz_zscore"], label="Ideal (Natural)", color="#2b5c8f", lw=1.8)
    axes[0].plot(df_flawed["start"], df_flawed["f0_hz_zscore"], label=f"Flawed ({flaw_name})", color="#d9534f", lw=1.8, linestyle="--")
    axes[0].set_ylabel("Pitch ($F_0$) Z-Score")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="upper right")

    # 2. Local Speech Rate (Words / Sec)
    axes[1].plot(df_ideal["start"], df_ideal["speech_rate"], label="Ideal Cadence", color="#2b5c8f", lw=1.8)
    axes[1].plot(df_flawed["start"], df_flawed["speech_rate"], label="Flawed Cadence", color="#d9534f", lw=1.8, linestyle="--")
    axes[1].set_ylabel("Speech Rate (wps)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="upper right")

    # 3. Inter-Word Pause Gaps (Dead Air Duration)
    axes[2].bar(df_ideal["start"], df_ideal["pause_before"], width=0.3, label="Ideal Pause Gaps", color="#2b5c8f", alpha=0.6)
    axes[2].bar(df_flawed["start"], df_flawed["pause_before"], width=0.3, label="Flawed Pause Gaps", color="#d9534f", alpha=0.6)
    axes[2].set_ylabel("Pause Before (s)")
    axes[2].set_xlabel("Timeline (seconds)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="upper right")

    out_plot = os.path.join(speech_dir, "acoustic_contrast_verification.png")
    plt.tight_layout()
    plt.savefig(out_plot, dpi=200)
    plt.close()
    print(f"\n[OK] Plot saved to: {out_plot}")

if __name__ == "__main__":
    plot_ideal_vs_flawed()