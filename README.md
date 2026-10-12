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

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) | `^0.115` | High-performance asynchronous REST API & streaming static server |
| **ASR & Alignment** | [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) | `^1.2` | Fast CTranslate2 Whisper implementation for word-level timestamps |
| **Audio Processing** | [Librosa](https://librosa.org/) | `^0.11` | Feature extraction: pYIN pitch tracking, RMS energy, spectral features |
| **Scientific Stack** | NumPy / SciPy / Pandas | Latest | Statistical z-score normalization, signal processing, metrics logging |
| **Audio I/O** | SoundFile & FFmpeg | — | Lossless PCM reading, conversion, and EBU R128 loudness normalization |
| **Frontend Framework**| [React](https://react.dev/) | `^19.2` | Component-driven reactive user interface |
| **Build Tooling** | [Vite](https://vitejs.dev/) | `^8.3` | Fast HMR dev server and production asset bundling |
| **Styling** | [Tailwind CSS](https://tailwindcss.com/) | `^3.4` | Responsive dark-mode styling and modern UI tokens |
| **Audio Visualization**| [WaveSurfer.js](https://wavesurfer.js.org/) | `^8.0` | Interactive audio waveform rendering and synchronized playback |
| **Data Visualization** | [Apache ECharts](https://echarts.apache.org/) | `^6.1` | Synchronized multi-track acoustic feature charts (Pitch & Energy) |
| **Icons & Motion** | Lucide React & Framer Motion | Latest | Sleek icons and smooth UI transitions |

---

## Dataset & Google Drive Access

The Oscine benchmark dataset contains **54 calibrated speech clips** across 6 world-class orators, paired with 3-tier severity flaw mirrors. All baselines are normalized to **16 kHz 16-bit PCM Mono** at **-20.0 LUFS (EBU R128)**.

### Speaker Baseline Matrix

| ID | Orator | Gender | Accent | Source Address | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `speech_01` | Michelle Obama | Female | US English | 2016 Democratic National Convention | ~62s |
| `speech_02` | Sudha Murty | Female | Indian English | Keynote & Public Address | ~60s |
| `speech_03` | Emma Watson | Female | British English | UN Women HeForShe Campaign | ~60s |
| `speech_04` | Dr. Shashi Tharoor | Male | Indian English | Oxford Union Debate Address | ~60s |
| `speech_05` | Andrew Ng | Male | US English | Educational Keynote & Talk | ~60s |
| `speech_06` | Chimamanda Ngozi Adichie | Female | Nigerian English | Commonwealth Lecture Address | ~60s |

### Dataset Download

> [!IMPORTANT]
> **Google Drive Dataset Link:**  
> 🔗 **[Download Complete Oscine Dataset (Google Drive)](PASTE_YOUR_GOOGLE_DRIVE_LINK_HERE)**  
> *(Replace the placeholder above with your actual Google Drive sharing URL)*

#### Dataset Setup Steps:
1. Download the archive (`oscine_dataset.zip`) from the Google Drive link above.
2. Extract the contents directly into the project root so the folder structure matches:
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

## Contrastive Flaw Matrix

Each baseline was synthetically perturbed across 3 distinct flaw axes using anchor-based signal synthesis (`src/inject.py`):

| Flaw Category | Target Anchor | Level 1 (Mild) | Level 2 (Moderate) | Level 3 (Severe) | Grounding Metric |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Errant Pause** | Anchor $t \approx 18.0\text{s}$ | $+1.2\text{s}$ hesitation | $+2.2\text{s}$ disruption | $+3.8\text{s}$ rhetorical stall | Gap duration $> 0.45\text{s}$ vs baseline |
| **Rushed Delivery** | Anchor $t \approx 25\text{s}-30\text{s}$ | $1.30\times$ speedup | $1.55\times$ speedup | $1.80\times$ speedup | Token rate ratio $\ge 1.15\times$ |
| **Monotone Pitch** | Anchor $t \approx 35\text{s}-44\text{s}$ | $55\%$ variance cut | $80\%$ variance cut | $95\%$ variance cut | $F_0$ variance $\le 70\%$ of reference |

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

**Author / Maintainer:** [aahanakabdugale](https://github.com/aahanakabdugale)  
**License:** Educational & Hackathon Use
