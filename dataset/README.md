# Oscine Contrastive Speech Analytics Dataset (Track C)

A curated, multimodal speech evaluation dataset engineered for **Track C: Contrastive Speech Analytics & Temporal Flaw Grounding** (Multimodal AI Hackathon 2026).

---

## 1. Dataset Overview

This dataset pairs high-quality rhetorical speech baselines ($L0$ ideal exemplars) with systematically calibrated, temporally localized acoustic disfluencies ($L1, L2, L3$ contrastive flaws).

* **Total Samples:** 60 audio clips (6 Reference Baselines + 54 Flaw Injections).
* **Audio Format:** 16,000 Hz, 16-bit PCM Linear Mono (`.wav`).
* **Loudness Standards:** EBU R128 Normalized to $-20.0 \text{ LUFS} \pm 0.5 \text{ LUFS}$.
* **Temporal Ground Truth:** Millisecond-accurate start/end timestamps for every flaw interval.
* **Transcripts:** Ground-truth text scripts with word-level phonetic alignment.

---

## 2. Directory Structure

```text
dataset/
├── metadata.csv                # Master tabular index (openable in Excel, Pandas, GitHub)
├── labels.json                 # Machine-readable ground truth interval boundaries
├── README.md                   # This documentation
│
├── speech_01/                  # Michelle Obama (US English, Female)
│   ├── ideal.wav               # 60s reference baseline
│   ├── ideal.aligned.json      # Word-level Whisper forced alignment
│   ├── ideal.features.json     # Precomputed acoustic features (F0, RMS, MFCC)
│   ├── transcript.txt          # Reference keynote speech script
│   ├── flawed_pause_L1.wav     # Mild hesitation (1.20s)
│   ├── flawed_pause_L2.wav     # Moderate disruption (2.20s)
│   ├── flawed_pause_L3.wav     # Severe dead air (3.80s)
│   ├── flawed_rushed_L1.wav    # Mild pacing speedup (1.30x)
│   ├── flawed_rushed_L2.wav    # Moderate pacing compression (1.60x)
│   ├── flawed_rushed_L3.wav    # Severe frantic delivery (2.10x)
│   ├── flawed_monotone_L1.wav  # Mild pitch flattening (55% σ)
│   ├── flawed_monotone_L2.wav  # Moderate robotic delivery (30% σ)
│   └── flawed_monotone_L3.wav  # Severe affective collapse (10% σ)
│
├── speech_02/                  # Sudha Murty (Indian English, Female)
├── speech_03/                  # Emma Watson (British English, Female)
├── speech_04/                  # Dr. Shashi Tharoor (Indian English, Male)
├── speech_05/                  # Andrew Ng (US English, Male)
└── speech_06/                  # Chimamanda Ngozi Adichie (Nigerian English, Female)
```

---

## 3. Metadata Manifest (`metadata.csv`)

The tabular file [`metadata.csv`](./metadata.csv) indexes all 60 clips in the dataset. It can be loaded directly into Pandas or viewed in Microsoft Excel:

```python
import pandas as pd
df = pd.read_csv("dataset/metadata.csv")
print(df[["speaker_name", "flaw_type", "severity_tier", "flaw_duration_sec"]].head())
```

### Schema Definition:
| Column | Type | Description |
| :--- | :--- | :--- |
| `sample_id` | String | Unique sample identifier (e.g., `speech_04_pause_L2`) |
| `speaker_id` | String | Speaker folder identifier (`speech_01` to `speech_06`) |
| `speaker_name` | String | Orator / public keynote speaker name |
| `accent_gender` | String | Demographic, dialectal accent, and gender profile |
| `category` | String | `Ideal Baseline` or `Contrastive Flaw` |
| `flaw_type` | String | `none`, `errant_pause`, `rushed_delivery`, `monotone_pitch` |
| `severity_tier` | String | `L0` (ideal), `L1` (mild), `L2` (moderate), `L3` (severe) |
| `audio_file` | Path | Relative path to 16 kHz `.wav` audio |
| `transcript_file` | Path | Relative path to reference text transcript |
| `alignment_file` | Path | Relative path to word-level timestamp JSON |
| `features_file` | Path | Relative path to time-series feature extraction JSON |
| `paired_baseline_audio` | Path | Direct reference exemplar for contrastive subtraction |
| `flaw_start_sec` | Float | Millisecond-accurate start time of injected anomaly |
| `flaw_end_sec` | Float | Millisecond-accurate end time of injected anomaly |
| `flaw_duration_sec` | Float | Net duration of the acoustic anomaly ($t_{\text{end}} - t_{\text{start}}$) |
| `total_duration_sec` | Float | Complete length of the audio file in seconds |
| `flaw_description` | String | Detailed clinical/rhetorical description of the flaw |

---

## 4. Acoustic Baseline Distribution

The 6 reference speakers provide diverse vocal registers, fundamental frequency medians ($F_0$), and speech rates across genders and global English dialects:

| Speaker ID | Orator | Gender | Dialect / Accent | Source Address | Mean $F_0$ | Mean WPS |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `speech_01` | Michelle Obama | Female | US English | 2016 DNC Address | ~185 Hz | 2.50 wps |
| `speech_02` | Sudha Murty | Female | Indian English | Keynote Public Address | ~195 Hz | 2.45 wps |
| `speech_03` | Emma Watson | Female | British English | UN Women HeForShe Speech | ~210 Hz | 2.38 wps |
| `speech_04` | Dr. Shashi Tharoor | Male | Indian English | Oxford Union Debate | ~132 Hz | 2.62 wps |
| `speech_05` | Andrew Ng | Male | US English | Stanford AI Lecture | ~125 Hz | 2.20 wps |
| `speech_06` | Chimamanda Ngozi Adichie | Female | Nigerian English | Commonwealth Lecture | ~190 Hz | 2.30 wps |

---

## 5. Synthetic Flaw Spectrum Calibration

All contrastive flaws are generated from the $L0$ baselines using digital signal processing ([`src/inject.py`](../src/inject.py)) to ensure ground-truth precision:

1. **Errant Pauses (`errant_pause`)**:
   - Injected at syntactically impermissible positions (e.g., between subject and verb).
   - **$L1$ (Mild):** $1.20\text{s}$ pause duration.
   - **$L2$ (Moderate):** $2.20\text{s}$ pause duration.
   - **$L3$ (Severe):** $3.80\text{s}$ pause duration.

2. **Rushed Delivery (`rushed_delivery`)**:
   - Time-scale pitch-synchronous overlap-add (WSOLA / phase-vocoder) acceleration across a critical clause.
   - **$L1$ (Mild):** $1.30\times$ tempo acceleration.
   - **$L2$ (Moderate):** $1.60\times$ tempo acceleration.
   - **$L3$ (Severe):** $2.10\times$ tempo acceleration.

3. **Monotone Pitch (`monotone_pitch`)**:
   - Fundamental frequency ($F_0$) variance compression centered around the speaker's median register.
   - **$L1$ (Mild):** $55\%$ variance retention ($\sigma_{\text{flawed}} = 0.55 \cdot \sigma_{\text{ref}}$).
   - **$L2$ (Moderate):** $30\%$ variance retention ($\sigma_{\text{flawed}} = 0.30 \cdot \sigma_{\text{ref}}$).
   - **$L3$ (Severe):** $10\%$ variance retention (rigid robotic flatline).

---

## 6. Validation and Benchmarking

This dataset serves as the benchmark ground truth evaluated by [`src/evaluate.py`](../src/evaluate.py), demonstrating strictly monotonic rubric score degradation across severity tiers:

$$\text{Tier } L0 (10.0) \;\longrightarrow\; \text{Tier } L1 (7.13) \;\longrightarrow\; \text{Tier } L2 (6.88) \;\longrightarrow\; \text{Tier } L3 (6.86)$$

Detailed evaluations and per-sample anomaly detection statistics are documented in [`results.csv`](../results.csv).
