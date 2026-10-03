# Oscine: Contrastive Speech Analytics & Temporal Flaw Grounding
> **Multimodal AI Hackathon 2026 — Track C**  
> *Objective: Develop an objective, contrastive speech evaluation engine that temporally bounds delivery flaws, explains their mathematical rationale, and scores spoken performances against elite rhetorical baselines.*

---

## 1. Executive Summary & Problem Overview
Evaluating competitive spoken performances (Interpretive Reading, Declamation, Extemporaneous, and Persuasive Oratory) is traditionally plagued by subjectivity and vague feedback. Participants lose points without understanding the precise acoustic failure point.

**Oscine** solves this by:
1. **Engineering a 54-clip Contrastive Speech Dataset** across 6 diverse world-class orators, pairing baseline performances with calibrated 3-tier severity flaw mirrors.
2. **Employing Speaker-Agnostic Acoustic Feature Extraction** ($F_0$ pitch tracking via pYIN, RMS energy contours, speech rate, pause topology, and MFCCs).
3. **Temporally Grounding Anomalies** to exact millisecond intervals via forced alignment and sliding-window contrastive delta analysis.
4. **Generating Causal Mathematical Explanations** that translate raw acoustic deltas into actionable coaching insights.
5. **Interactive Full-Stack Dashboard** featuring real-time audio playback, synchronized waveform/feature overlays, and evaluative rubric scoring.

---

## 2. Dataset Architecture & Contrastive Flaw Matrix

### 2.1 The "Ideal" Baselines
We curated high-fidelity keynote recordings from 6 prominent speakers across diverse genders and global accents, normalized to **16 kHz 16-bit PCM Mono** and **EBU R128 (-20 LUFS)**:

| ID | Speaker | Gender | Accent | Sourced Address |
| :--- | :--- | :--- | :--- | :--- |
| `speech_01` | Michelle Obama | Female | US English | 2016 DNC Address |
| `speech_02` | Sudha Murty | Female | Indian English | Keynote & Public Address |
| `speech_03` | Emma Watson | Female | British English | UN Women HeForShe Campaign |
| `speech_04` | Dr. Shashi Tharoor | Male | Indian English | Oxford Union Debate Address |
| `speech_05` | Andrew Ng | Male | US English | Stanford Keynote & AI Opportunities Address |
| `speech_06` | Chimamanda Ngozi Adichie | Female | Nigerian English | Commonwealth Lecture Address |

### 2.2 The "Flawed" Gradient Spectrum (54 Clips)
Using anchor-based signal synthesis (`src/inject.py`), each speaker's baseline was perturbed along 3 flaw axes across a 3-tier severity ladder:

| Flaw Type | Target Region | L1 Severity | L2 Severity | L3 Severity |
| :--- | :--- | :--- | :--- | :--- |
| **Errant Pause** | Anchor $t=18.0\text{s}$ | 1.2s hesitation | 2.2s disruption | 3.8s rhetorical stall |
| **Rushed Delivery** | Anchor $t=25.0\text{s}-30.0\text{s}$ | 1.30× speedup | 1.55× speedup | 1.80× compression |
| **Monotone Pitch** | Anchor $t=35.0\text{s}-44.0\text{s}$ | 55% variance cut | 80% variance cut | 95% variance cut |

All 54 clips have exact millisecond ground-truth annotations stored in both individual `dataset/speech_0X/labels.json` and unified `dataset/labels.json`.

---

## 3. Algorithmic Pipeline & Technical Methodology

```
┌─────────────────────────────────────────────────────────────┐
│                       INPUT AUDIO                           │
│           (Ideal Baseline  vs.  Test Recording)             │
└──────────────────────────────┬──────────────────────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
┌──────────────────────────────┐       ┌──────────────────────────────┐
│       FORCED ALIGNMENT       │       │  ACOUSTIC FEATURE EXTRACTION │
│  - Word-level timestamps     │       │  - pYIN F0 & Voicing Mask    │
│  - Pause detection (<15th %) │       │  - RMS Energy & Z-score      │
│  - Dynamic token matching    │       │  - Local Speech Rate (syl/s) │
└──────────────┬───────────────┘       └───────────────┬──────────────┘
               │                                       │
               └───────────────────────┬───────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────┐
│           TEMPORAL FLAW GROUNDING (detect.py)               │
│  - Paired word alignment across temporal timelines          │
│  - Contrastive delta evaluation (Pause, Rate, Pitch, RMS)   │
│  - Temporal gap merging (<= 0.4s) into continuous regions   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           CAUSAL EXPLANATIONS & RUBRIC (explain.py)         │
│  - Mathematical rationale (deviation metrics, z-scores)     │
│  - 4-Tier Rubric: Pacing, Intonation, Energy, Articulation  │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Feature Extraction (`src/features.py`)
- **Pitch Tracking ($F_0$)**: Uses probabilistic YIN (`librosa.pyin`) over $50\text{ Hz} - 450\text{ Hz}$ with hop size 256. Voiced frames are segmented per word to compute median $F_0$ and semitone standard deviation.
- **Energy Dynamics**: Root-Mean-Square (RMS) frame energy normalized via cross-utterance $z$-score to ensure speaker-agnostic volume comparisons.
- **Pause & Rate Computation**: Audio below $3\times$ the 15th energy percentile is marked as silence. Speech rate is computed per word-window in syllables per second.

### 3.2 Contrastive Detection (`src/detect.py`)
- Aligns test words to reference words using fuzzy Levenshtein token alignment.
- Computes local moving-window rate ratios $\frac{\text{duration}_{\text{ref}}}{\text{duration}_{\text{test}}}$.
- Flags:
  - **Errant Pause**: Silence interval $> 0.95\text{s}$ at non-syntactic boundaries.
  - **Rushed Delivery**: Local rate ratio $\ge 1.15\times$ baseline.
  - **Monotone Pitch**: Pitch variance drops $\le 65\%$ of baseline pitch variance.
  - **Volume Instability**: Cross-speaker normalized $|z_{\text{rms}} - z_{\text{ref}}| \ge 2.0\sigma$.

### 3.3 Causal Explainability (`src/explain.py`)
Each flaw region provides:
- Exact temporal boundary $[t_{\text{start}}, t_{\text{end}}]$ and word sequence.
- Precise metric deviation (e.g., *"+1.8s silence vs. 0.1s baseline"*, *"1.42× acceleration over 8 words"*).
- Pedagogical coaching recommendation for competitive speech improvement.

---

## 4. Evaluative Rubric Scoring
The engine outputs an objective **100-point composite rubric score** partitioned into 4 pillars:
1. **Cadence & Pacing (25 pts)**: Penalties for rushed bursts and tempo volatility.
2. **Pitch Modulation & Dynamic Range (25 pts)**: Penalties for monotone flatlines.
3. **Volume Consistency & Projection (25 pts)**: Penalties for erratic loudness drops.
4. **Pause Placement & Articulation (25 pts)**: Penalties for unnatural hesitations.

---

## 5. Quickstart & Reproducibility Guide

### 5.1 Prerequisites
- Python 3.10+
- Node.js 18+

### 5.2 Backend Setup
```bash
# Clone the repository
git clone https://github.com/aahanakabdugale/Oscine.git
cd Oscine

# Activate virtual environment
.\.venv\Scripts\activate   # On Windows
# source .venv/bin/activate # On Unix/macOS

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server (runs on http://localhost:8000)
cd src
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

### 5.3 Frontend Setup
```bash
# In a new terminal window:
cd frontend
npm install
npm run dev
# Open http://localhost:5173 in browser
```

### 5.4 Running Tests & Calibration
```bash
# Run unit tests
$env:PYTHONPATH="."; python tests/test_detection_alignment.py

# Regenerate / verify flaw dataset
python src/inject.py
python src/verify_labels.py
```

---

## 6. Repository Structure
```
Oscine/
├── dataset/                    # 6 Speakers x 10 clips = 60 audio files
│   ├── speech_01/ ... speech_06/
│   │   ├── ideal.wav           # Baseline audio (16kHz PCM)
│   │   ├── transcript.txt      # Reference text
│   │   ├── labels.json         # Ground-truth flaw boundaries
│   │   └── flawed_*.wav        # 9 Flaw variants (L1, L2, L3)
│   └── labels.json             # Consolidated ground truth
├── src/
│   ├── api.py                  # FastAPI REST endpoints
│   ├── align.py                # Forced alignment engine
│   ├── features.py             # pYIN F0, RMS, MFCC, speech rate
│   ├── detect.py               # Contrastive flaw grounding
│   ├── explain.py              # Causal rationale & rubrics
│   ├── inject.py               # Contrastive flaw synthesis
│   └── verify_labels.py        # Dataset auditor & calibration
├── frontend/                   # React + Vite + Tailwind dashboard
│   └── src/
│       ├── App.jsx             # Main interactive evaluation UI
│       └── components/         # Waveform & metrics visualizations
├── tests/                      # Unit & integration test suite
├── SOURCES.md                  # Baseline speaker attributions
└── README.md                   # System documentation
```
