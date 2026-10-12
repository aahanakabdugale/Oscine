# Oscine: Contrastive Speech Analytics & Temporal Flaw Grounding

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF.svg)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg)](https://tailwindcss.com/)
[![Status](https://img.shields.io/badge/Project-Hackathon%20Prototype-orange.svg)](#educational-hackathon-disclaimer)

> **Oscine** is an automated, contrastive speech evaluation engine that temporally bounds oratorical flaws (errant pauses, rushed delivery, monotone pitch, volume shifts), computes causal mathematical rationales, and evaluates spoken delivery against elite rhetorical baselines.

---

## System Architecture

```
  ┌───────────────────────────────────────────────────────────────┐
  │                         Input Audio                           │
  │            (Elite Baseline vs. User / Flawed Audio)           │
  └───────────────────────────────┬───────────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Word-Level Alignment        │       │   Acoustic Feature Extraction   │
│  - Faster-Whisper transcription │       │  - Probabilistic YIN (pYIN F0)  │
│  - Dynamic token alignment      │       │  - Frame-level RMS energy       │
│  - Inter-word silence discovery │       │  - Speech rate (Words / Sec)    │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
                 └────────────────────────┬────────────────┘
                                          ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                     Temporal Flaw Grounding Engine                        │
│   - Paired token delta computation (Pause, Rate, Pitch, Energy)           │
│   - Moving-window statistical deviation analysis (z-scores)               │
│   - Contiguous anomaly merging (<= 400ms delta threshold)                 │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    Causal Explanation & Rubric Scoring                    │
│   - Mathematical justification (severity magnitude & acoustic deltas)    │
│   - 10.0 Composite Rubric: Pacing, Intonation, Dynamic Range, Continuity  │
│   - Real-time React / WaveSurfer / ECharts multi-track visualization      │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend & API
| Technology | Version / Tooling | Purpose |
| :--- | :--- | :--- |
| **Python** | `3.10+` (3.11 recommended) | Core execution runtime for audio analytics and ML pipelines |
| [FastAPI](https://fastapi.tiangolo.com/) | `^0.115` | High-performance asynchronous REST API framework |
| [Uvicorn](https://www.uvicorn.org/) | `^0.34` | Lightning-fast ASGI web server for API endpoints and static streaming |

### Speech Processing & ML Pipeline
| Technology | Role | Purpose |
| :--- | :--- | :--- |
| [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) | ASR & Forced Alignment | CTranslate2-accelerated Whisper model generating word-level timestamps |
| [Librosa](https://librosa.org/) | Acoustic Feature Extraction | Probabilistic YIN (pYIN) pitch tracking, RMS energy contours, and STFT spectral analysis |
| NumPy & SciPy | Scientific Computing | Signal crossfading, moving-window statistics, and cross-utterance $z$-score normalization |
| SoundFile & FFmpeg | Audio I/O & Encoding | Lossless 16 kHz 16-bit PCM read/write and EBU R128 loudness normalization (-20 LUFS) |

### Frontend & Data Visualization
| Technology | Version / Tooling | Purpose |
| :--- | :--- | :--- |
| [React](https://react.dev/) | `^19.2` | Reactive component architecture for interactive evaluation dashboard |
| [Vite](https://vitejs.dev/) | `^8.3` | Next-generation build tool with instant Hot Module Replacement (HMR) |
| [Tailwind CSS](https://tailwindcss.com/) | `^3.4` | Modern utility-first CSS styling with unified dark-mode tokens |
| [WaveSurfer.js](https://wavesurfer.js.org/) | `^8.0` | Interactive audio waveform rendering and synchronized playback scrubbing |
| [Apache ECharts](https://echarts.apache.org/) | `^6.1` (`echarts-for-react`) | Synchronized multi-track crosshair visualizer for pitch and volume contours |
| Lucide React & Framer Motion | Latest | Modern icon set and smooth micro-animations |

---

## Dataset & Google Drive Access

Oscine benchmark dataset consists of **54 calibrated speech clips** spanning 6 diverse global orators, paired with 3-tier severity flaw mirrors (errant pauses, rushed pacing, monotone intonation). Audio recordings are normalized to **16 kHz 16-bit PCM Mono** at **-20.0 LUFS (EBU R128)**.

> [!NOTE]
> *Full orator attribution and speech provenance are documented in [`SOURCES.md`](./SOURCES.md). Detailed flaw calibration formulas and label schemas are documented in [`dataset/README.md`](./dataset/README.md) and the accompanying project report.*

### Dataset Download

> [!IMPORTANT]
> **Google Drive Dataset Link:**  
> 🔗 **[Download Complete Oscine Dataset (Google Drive)]((https://drive.google.com/file/d/1eq33VpF9Ev41haum4Vl4sAh6z1U2vsR7/view?usp=sharing))**  


#### Extraction & Placement:
Download and extract the dataset archive (`oscine_dataset.zip`) into the project root:
```text
Oscine/
└── dataset/
    ├── labels.json
    ├── metadata.csv
    ├── speech_01/ ... speech_06/
    │   ├── ideal.wav
    │   ├── transcript.txt
    │   ├── labels.json
    │   └── flawed_*.wav
```

---

## Prerequisites & System Requirements

Ensure the following tools are installed on your host system:

| Dependency | Minimum Version | Verification Command | Notes |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10+ (3.11 recommended) | `python --version` | Required for backend and ML pipeline |
| **Node.js** | 18+ (20+ recommended) | `node --version` | Required for frontend UI |
| **npm** | 9+ | `npm --version` | Node package manager |
| **FFmpeg** | Any modern release | `ffmpeg -version` | Audio transcoding; must be available in system `PATH` |
| **Git** | Any modern release | `git --version` | Version control |

---

## Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/aahanakabdugale/Oscine.git
cd Oscine
```

### 2. Backend Environment Setup
Create and activate an isolated virtual environment, then install Python dependencies:

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Frontend Setup
Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

Oscine operates with a FastAPI backend service and a Vite + React frontend dashboard.

### Terminal 1: Start Backend API
```bash
# Ensure virtual environment is activated
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```
- API health check: [http://localhost:8000/health](http://localhost:8000/health)
- Swagger documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### Terminal 2: Start Frontend UI
```bash
cd frontend
npm run dev
```
- Interactive Dashboard: [http://localhost:5173](http://localhost:5173)

---

## API Reference

| Method | Endpoint | Description | Payload / Parameters | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Service health status | None | `{"status": "ok", "app": "..."}` |
| `GET` | `/api/references` | Lists all baseline orators and metadata | None | JSON array of reference speech models |
| `POST` | `/api/analyze` | Contrastive evaluation of input audio | Multipart Form: `reference_id`, `audio` (file), `transcript` (opt) | Millisecond flaw bounds, z-scores, rubric scores, diagnostic explanations |

---

## Evaluation & Benchmark

Validate the acoustic engine and forced-alignment subsystem locally:

```bash
# Run full benchmark evaluation (IoU hit-rate & severity monotonicity)
python src/evaluate.py

# Run unit tests and detection alignment verification
python tests/test_detection_alignment.py
```

---

## AI Assistance Disclosure

In full compliance with hackathon submission guidelines, AI coding assistants were utilized during the development of this repository.

| Tool | Model / Provider | Primary Application Areas |
| :--- | :--- | :--- |
| **Antigravity IDE** | Google Gemini & Anthropic Claude | UI layout scaffolding, ECharts multi-track crosshair synchronization logic, mathematical crossfade formulation for audio perturbation, and automated test harness scripting. |

**Specific Contributions:**
1. **Frontend Visualization:** Assisted in structuring cross-synchronized WaveSurfer.js playback with Apache ECharts feature tracks.
2. **Audio Perturbation Math:** Co-engineered boundary crossfading logic in `src/inject.py` to prevent phase-cancellation artifacts during splicing.
3. **Causal Explanation Engine:** Templated numeric z-score translations into actionable oratorical feedback in `src/explain.py`.

---

## Educational Hackathon Disclaimer

> [!NOTE]
> **Hackathon & Educational Notice:**  
> This project was developed as an exploratory prototype for the **Multimodal AI Hackathon 2026** strictly for **educational and research purposes**. It is designed to demonstrate contrastive speech analytics concepts and is not intended or certified for commercial production, clinical diagnosis, or speech-language pathology assessment.

---


