# Acoustic Dataset Baseline & Attribution (Track C)

| Folder | Speaker | Gender | Accent | Source Keynote / Address | Duration | Preprocessing |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `speech_01` | Michelle Obama | Female | US English | 2016 Democratic National Convention | ~62s | Gating + EBU R128 (-20 LUFS) |
| `speech_02` | Sudha Murty | Female | Indian English | Keynote & Public Address | ~60s | Gating + EBU R128 (-20 LUFS) |
| `speech_03` | Emma Watson | Female | British English | UN Women HeForShe Campaign | ~60s | Gating + EBU R128 (-20 LUFS) |
| `speech_04` | Dr. Shashi Tharoor | Male | Indian English | Oxford Union Debate Address | ~60s | Gating + EBU R128 (-20 LUFS) |
| `speech_05` | Andrew Ng | Male | US English | Ted Talk | ~60s | Gating + EBU R128 (-20 LUFS) |
| `speech_06` | Chimamanda Ngozi Adichie | Female | Nigerian English |  Lecture Address | ~60s | Gating + EBU R128 (-20 LUFS) |

### Standards:
* **Audio Format:** 16,000 Hz, 16-bit PCM Mono (`.wav`)
* **Loudness:** EBU R128 Normalized to -20.0 LUFS ($\pm 0.5$ LUFS)
* **Ground Truth:** Formatted with millisecond bounds in `dataset/speech_0X/labels.json`
