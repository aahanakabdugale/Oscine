import React, { useState, useEffect, useRef } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play, Pause, Upload, CheckCircle2, AlertTriangle,
  BarChart2, Sun, Moon, Volume2, ShieldCheck, Download,
  Sparkles, Layers, Sliders, FileAudio, FileText, Check, ChevronDown, ChevronUp, Eye,
  Mic, Zap, Brain, Activity, TrendingDown, Clock, Radio, Timer, Gauge
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const DIMENSION_CONFIG = {
  errant_pause: {
    title: 'Errant Pause',
    subtitle: 'Hesitation & Silence',
    icon: Timer,

    gradient: 'from-amber-500 to-orange-500',
    border: 'border-amber-200 dark:border-amber-500/30',
    text: 'text-amber-700 dark:text-amber-300',
    badge: 'bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-300',
    glow: 'shadow-amber-500/25',
    activeBg: 'border-amber-500 bg-amber-50 dark:bg-amber-500/15 text-amber-800 dark:text-amber-300 ring-2 ring-amber-500/30',
  },
  rushed_delivery: {
    title: 'Rushed Delivery',
    subtitle: 'Syllabic Acceleration',
    icon: Zap,

    gradient: 'from-rose-500 to-pink-600',
    border: 'border-rose-200 dark:border-rose-500/30',
    text: 'text-rose-700 dark:text-rose-300',
    badge: 'bg-rose-100 text-rose-900 dark:bg-rose-950/60 dark:text-rose-300',
    glow: 'shadow-rose-500/25',
    activeBg: 'border-rose-500 bg-rose-50 dark:bg-rose-500/15 text-rose-800 dark:text-rose-300 ring-2 ring-rose-500/30',
  },
  monotone_pitch: {
    title: 'Monotone Pitch',
    subtitle: 'Flattened Inflection',
    icon: Activity,

    gradient: 'from-violet-600 to-indigo-600',
    border: 'border-violet-200 dark:border-violet-500/30',
    text: 'text-violet-700 dark:text-violet-300',
    badge: 'bg-violet-100 text-violet-900 dark:bg-violet-950/60 dark:text-violet-300',
    glow: 'shadow-violet-500/25',
    activeBg: 'border-violet-500 bg-violet-50 dark:bg-violet-500/15 text-violet-800 dark:text-violet-300 ring-2 ring-violet-500/30',
  },
  volume_instability: {
    title: 'Volume Instability',
    subtitle: 'Dynamic Energy Swing',
    icon: Volume2,

    gradient: 'from-cyan-500 to-blue-600',
    border: 'border-cyan-200 dark:border-cyan-500/30',
    text: 'text-cyan-700 dark:text-cyan-300',
    badge: 'bg-cyan-100 text-cyan-900 dark:bg-cyan-950/60 dark:text-cyan-300',
    glow: 'shadow-cyan-500/25',
    activeBg: 'border-cyan-500 bg-cyan-50 dark:bg-cyan-500/15 text-cyan-800 dark:text-cyan-300 ring-2 ring-cyan-500/30',
  },
  vocal_clarity_drift: {
    title: 'Vocal Clarity Drift',
    subtitle: 'Spectral Timbre Shift',
    icon: Sparkles,

    gradient: 'from-emerald-500 to-teal-600',
    border: 'border-emerald-200 dark:border-emerald-500/30',
    text: 'text-emerald-700 dark:text-emerald-300',
    badge: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300',
    glow: 'shadow-emerald-500/25',
    activeBg: 'border-emerald-500 bg-emerald-50 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 ring-2 ring-emerald-500/30',
  },
};

const PRESET_GROUPS = [
  {
    key: 'errant_pause',
    group: 'Errant Pause',
    subtitle: 'Hesitation & Silence',
    icon: Timer,

    gradient: 'from-amber-500 to-orange-500',
    glow: 'shadow-amber-500/25',
    activeBg: 'border-amber-500 bg-amber-50 dark:bg-amber-500/15 text-amber-800 dark:text-amber-300 ring-2 ring-amber-500/30',
    badge: 'bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-300 border-amber-300/40',
    items: ['flawed_pause_L1', 'flawed_pause_L2', 'flawed_pause_L3']
  },
  {
    key: 'rushed_delivery',
    group: 'Rushed Delivery',
    subtitle: 'Pacing Acceleration',
    icon: Zap,

    gradient: 'from-rose-500 to-pink-600',
    glow: 'shadow-rose-500/25',
    activeBg: 'border-rose-500 bg-rose-50 dark:bg-rose-500/15 text-rose-800 dark:text-rose-300 ring-2 ring-rose-500/30',
    badge: 'bg-rose-100 text-rose-900 dark:bg-rose-950/60 dark:text-rose-300 border-rose-300/40',
    items: ['flawed_rushed_L1', 'flawed_rushed_L2', 'flawed_rushed_L3']
  },
  {
    key: 'monotone_pitch',
    group: 'Monotone Pitch',
    subtitle: 'Flattened Inflection',
    icon: Activity,

    gradient: 'from-violet-600 to-indigo-600',
    glow: 'shadow-violet-500/25',
    activeBg: 'border-violet-500 bg-violet-50 dark:bg-violet-500/15 text-violet-800 dark:text-violet-300 ring-2 ring-violet-500/30',
    badge: 'bg-violet-100 text-violet-900 dark:bg-violet-950/60 dark:text-violet-300 border-violet-300/40',
    items: ['flawed_monotone_L1', 'flawed_monotone_L2', 'flawed_monotone_L3']
  },
];

const SEVERITY_LABELS = { L1: 'Mild', L2: 'Moderate', L3: 'Severe' };

const ScoreRing = ({ value, label, icon: Icon, emoji }) => {
  const pct = (value / 10) * 100;
  const circumference = 2 * Math.PI * 28;
  const strokeDash = (pct / 100) * circumference;
  const colors = {
    good: '#10b981',
    mid: '#6366f1',
    bad: '#f43f5e',
  };
  const c = value >= 8 ? colors.good : value >= 5 ? colors.mid : colors.bad;
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-20 h-20">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 64 64">
          <circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" className="text-slate-200 dark:text-slate-700" strokeWidth="5" />
          <circle cx="32" cy="32" r="28" fill="none" stroke={c} strokeWidth="5"
            strokeDasharray={`${strokeDash} ${circumference}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 1s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-black" style={{ color: c }}>{value.toFixed(1)}</span>
          <span className="text-[9px] text-slate-400 font-medium">/ 10</span>
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        {emoji && <span className="text-xs">{emoji}</span>}
        {Icon && <Icon className="w-3.5 h-3.5 text-slate-500" />}
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300 text-center leading-tight">{label}</span>
      </div>
    </div>
  );
};

export default function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [references, setReferences] = useState([]);
  const [selectedRef, setSelectedRef] = useState(null);

  const [activeTabMode, setActiveTabMode] = useState("upload");
  const [audioFile, setAudioFile] = useState(null);
  const [transcriptFile, setTranscriptFile] = useState(null);
  const [activeTranscriptText, setActiveTranscriptText] = useState("");
  const [showTranscriptDrawer, setShowTranscriptDrawer] = useState(false);
  const [selectedPresetName, setSelectedPresetName] = useState(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeProgress, setAnalyzeProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [filterCategory, setFilterCategory] = useState("all");

  const waveformRef = useRef(null);
  const wavesurfer = useRef(null);
  const regionsPlugin = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  const chartRefPitch = useRef(null);
  const chartRefRate = useRef(null);
  const chartRefPause = useRef(null);

  const audioInputRef = useRef(null);
  const transcriptInputRef = useRef(null);

  useEffect(() => {
    if (darkMode) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  }, [darkMode]);

  useEffect(() => {
    fetch(`${API_BASE}/api/references`)
      .then(res => res.json())
      .then(data => {
        setReferences(data);
        // No default — user must choose
      })
      .catch(err => console.error("Error fetching baseline models:", err));
  }, []);

  // Simulated progress during analysis
  useEffect(() => {
    let interval;
    if (isAnalyzing) {
      setAnalyzeProgress(0);
      interval = setInterval(() => {
        setAnalyzeProgress(p => p < 88 ? p + Math.random() * 8 : p);
      }, 400);
    } else {
      setAnalyzeProgress(100);
    }
    return () => clearInterval(interval);
  }, [isAnalyzing]);

  const handleRefChange = (refId) => {
    setSelectedRef(refId);
    const chosen = references.find(r => r.id === refId);
    if (chosen && chosen.transcript && !transcriptFile) {
      setActiveTranscriptText(chosen.transcript);
    }
  };

  const initWaveform = (audioUrl, flawRegions = []) => {
    if (wavesurfer.current) wavesurfer.current.destroy();

    const ws = WaveSurfer.create({
      container: waveformRef.current,
      waveColor: darkMode ? ['#6366f1', '#8b5cf6', '#a78bfa'] : ['#818cf8', '#a5b4fc'],
      progressColor: darkMode ? '#c4b5fd' : '#4f46e5',
      cursorColor: darkMode ? '#f8fafc' : '#0f172a',
      cursorWidth: 2,
      height: 100,
      barWidth: 2,
      barGap: 2,
      barRadius: 4,
      normalize: true,
      fillParent: true,
    });

    const wsRegions = ws.registerPlugin(RegionsPlugin.create());
    regionsPlugin.current = wsRegions;
    ws.load(audioUrl);

    ws.on('ready', () => {
      wsRegions.clearRegions();
      flawRegions.forEach((reg, i) => {
        wsRegions.addRegion({
          id: `flaw_${i}`,
          start: reg.start,
          end: reg.end,
          color: 'rgba(244, 63, 94, 0.2)',
          drag: false,
          resize: false,
        });
      });
    });

    ws.on('audioprocess', () => setCurrentTime(ws.getCurrentTime()));
    ws.on('play', () => setIsPlaying(true));
    ws.on('pause', () => setIsPlaying(false));
    ws.on('finish', () => setIsPlaying(false));
    wavesurfer.current = ws;
  };

  const handleSelectUploadMode = () => {
    setActiveTabMode("upload");
    setSelectedPresetName(null);
    setTranscriptFile(null);
    setActiveTranscriptText("");
  };

  const handleSelectPreset = async (flawName) => {
    if (!selectedRef) { alert("Please select a Reference Baseline first."); return; }
    setActiveTabMode("preset");
    setSelectedPresetName(flawName);
    try {
      const url = `${API_BASE}/static/dataset/${selectedRef}/${flawName}.wav`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("Could not find file on server.");
      const blob = await res.blob();
      const file = new File([blob], `${flawName}.wav`, { type: 'audio/wav' });
      setAudioFile(file);
      setTranscriptFile(null);
      const chosen = references.find(r => r.id === selectedRef);
      if (chosen && chosen.transcript) setActiveTranscriptText(chosen.transcript);
    } catch (err) {
      alert("Failed to load preset: " + err.message);
    }
  };

  const handleAudioUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      setAudioFile(e.target.files[0]);
      setSelectedPresetName(null);
      setActiveTabMode("upload");
    }
  };

  const handleTranscriptUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setTranscriptFile(file);
      const reader = new FileReader();
      reader.onload = (event) => setActiveTranscriptText(event.target.result);
      reader.readAsText(file);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedRef) { alert("Please select a Reference Baseline first."); return; }
    if (!audioFile) { alert("Please upload a .wav audio file or pick a benchmark preset first."); return; }
    setIsAnalyzing(true);
    const formData = new FormData();
    formData.append("reference_id", selectedRef);
    formData.append("audio", audioFile);
    if (activeTabMode === "preset" && activeTranscriptText.trim()) {
      formData.append("transcript", activeTranscriptText.trim());
    } else if (activeTabMode === "upload" && transcriptFile && activeTranscriptText.trim()) {
      formData.append("transcript", activeTranscriptText.trim());
    }
    try {
      const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: formData });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || "Analysis failed."); }
      const data = await res.json();
      setResult(data);
      const targetAudioStream = `${API_BASE}${data.audio_url}`;
      setTimeout(() => initWaveform(targetAudioStream, data.regions), 120);
      setTimeout(() => {
        if (chartRefPitch.current && chartRefRate.current && chartRefPause.current) {
          echarts.connect([
            chartRefPitch.current.getEchartsInstance(),
            chartRefRate.current.getEchartsInstance(),
            chartRefPause.current.getEchartsInstance(),
          ]);
        }
      }, 300);
    } catch (err) {
      alert("Analysis error: " + err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const exportDiagnosticReport = () => {
    if (!result) return;
    const reportData = {
      title: "Oscine Speech Analytics Diagnostic Report",
      generated_at: new Date().toISOString(),
      reference_speaker: selectedRef || "Custom Baseline",
      evaluated_target: audioFile ? audioFile.name : (selectedPreset || "Speech Sample"),
      duration_seconds: result.duration,
      rubric_scores: {
        overall_composite: Number(result.scores.overall_score.toFixed(2)),
        pacing_cadence: Number(result.scores.pacing_score.toFixed(2)),
        pause_continuity: Number(result.scores.pauses_score.toFixed(2)),
        volume_stability: Number(result.scores.volume_score.toFixed(2)),
        pitch_expressiveness: Number(result.scores.expressiveness_score.toFixed(2)),
        text_alignment_ratio: result.text_alignment_ratio !== undefined ? Number(result.text_alignment_ratio.toFixed(3)) : null,
      },
      anomalies_detected_count: result.regions ? result.regions.length : 0,
      anomalies: (result.regions || []).map((r, i) => ({
        index: i + 1,
        flaw_type: r.flaw_type,
        start_seconds: r.t_start,
        end_seconds: r.t_end,
        duration_seconds: Number((r.t_end - r.t_start).toFixed(2)),
        max_sigma_deviation: r.max_sigma,
        affected_words: r.words,
        causal_explanation: r.explanation,
      })),
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `oscine_diagnostic_report_${selectedRef || "speech"}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const jumpToTime = (start) => {
    if (!wavesurfer.current) return;
    wavesurfer.current.seekTo(start / wavesurfer.current.getDuration());
    wavesurfer.current.play();
  };

  const makeChartOption = (title, refData, partData, yName, regions) => {
    const textColor = darkMode ? '#94a3b8' : '#64748b';
    const splitLineColor = darkMode ? '#1e293b' : '#f1f5f9';
    const markAreas = regions.map(r => ([
      { xAxis: r.start, itemStyle: { color: darkMode ? 'rgba(244, 63, 94, 0.15)' : 'rgba(244, 63, 94, 0.10)' } },
      { xAxis: r.end }
    ]));
    return {
      title: { text: title, textStyle: { color: textColor, fontSize: 12, fontWeight: 700, fontFamily: 'Inter' } },
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', lineStyle: { color: '#f43f5e', type: 'dashed', width: 1 } },
        backgroundColor: darkMode ? '#131b2a' : '#ffffff',
        borderColor: darkMode ? '#2d3748' : '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: darkMode ? '#f8fafc' : '#0f172a', fontSize: 12 }
      },
      legend: {
        data: ['Ideal Reference', 'Participant'],
        textStyle: { color: textColor, fontSize: 11 },
        right: 0, top: 0
      },
      grid: { left: 48, right: 15, top: 32, bottom: 24 },
      xAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: splitLineColor } },
        splitLine: { show: false },
        axisLabel: { color: textColor, fontSize: 10, formatter: '{value}s' }
      },
      yAxis: {
        type: 'value', name: yName,
        nameTextStyle: { color: textColor, fontSize: 10 },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: splitLineColor, type: 'dashed' } },
        axisLabel: { color: textColor, fontSize: 10 }
      },
      series: [
        {
          name: 'Ideal Reference', type: 'line', smooth: true, showSymbol: false,
          data: refData, lineStyle: { width: 2.5, color: '#6366f1' },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
                { offset: 0, color: 'rgba(99,102,241,0.15)' }, { offset: 1, color: 'rgba(99,102,241,0)' }
              ]
            }
          },
          markArea: { silent: true, data: markAreas }
        },
        {
          name: 'Participant', type: 'line', smooth: true, showSymbol: false,
          data: partData, lineStyle: { width: 2, color: '#f59e0b', type: 'dashed' }
        }
      ]
    };
  };

  const filteredRegions = result?.regions.filter(r => {
    if (filterCategory === "all") return true;
    return r.dimension.includes(filterCategory);
  }) || [];

  const wordCount = activeTranscriptText.trim() ? activeTranscriptText.trim().split(/\s+/).length : 0;

  const getFlawKey = (dimension) => {
    if (dimension.includes('pause')) return 'errant_pause';
    if (dimension.includes('rushed')) return 'rushed_delivery';
    if (dimension.includes('monotone')) return 'monotone_pitch';
    if (dimension.includes('volume')) return 'volume_instability';
    return 'errant_pause';
  };

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-[#080c14] text-slate-100' : 'bg-slate-50 text-slate-800'} transition-colors duration-300 pb-20`}>

      {/* Ambient background blobs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className={`absolute -top-40 -right-40 w-96 h-96 rounded-full blur-3xl ${darkMode ? 'bg-indigo-900/20' : 'bg-indigo-100/80'}`} />
        <div className={`absolute top-1/2 -left-40 w-80 h-80 rounded-full blur-3xl ${darkMode ? 'bg-violet-900/15' : 'bg-violet-100/60'}`} />
        <div className={`absolute bottom-0 right-1/4 w-64 h-64 rounded-full blur-3xl ${darkMode ? 'bg-cyan-900/10' : 'bg-cyan-100/40'}`} />
      </div>

      {/* ── NAVBAR ── */}
      <nav className={`border-b ${darkMode ? 'border-white/5 bg-[#080c14]/80' : 'border-slate-200/80 bg-white/80'} sticky top-0 z-50 glass-panel`}>
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 via-violet-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30 animate-float">
              <Radio className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold tracking-tight text-xl bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">Oscine</span>
              <span className="text-[10px] ml-2.5 px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-semibold uppercase tracking-wider">Prosody Engine</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setDarkMode(!darkMode)}
              className={`p-2.5 rounded-xl border transition-all hover:scale-105 active:scale-95 ${darkMode ? 'border-white/10 bg-white/5 text-amber-400 hover:bg-white/10' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 shadow-sm'}`}
              title="Toggle Theme"
            >
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <div className="hidden sm:flex items-center gap-2 text-sm font-medium text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-full border border-emerald-500/20">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              FastAPI Core Online
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 pt-8 space-y-6 relative z-10">

        {/* ── HERO BANNER (only before results) ── */}
        {!result && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`relative overflow-hidden rounded-3xl border ${darkMode ? 'border-white/8 bg-gradient-to-br from-indigo-950/60 to-[#0d1220]' : 'border-indigo-200/60 bg-gradient-to-br from-indigo-50 to-white'} p-8 shadow-xl`}
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-indigo-500/10 to-transparent rounded-3xl" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-cyan-500/10 to-transparent rounded-3xl" />
            <div className="relative flex flex-col md:flex-row items-start md:items-center gap-6">
              <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center shadow-2xl shadow-indigo-500/40 shrink-0">
                <Brain className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-black tracking-tight mb-2">
                  <span className="gradient-text">Contrastive Speech Analytics</span>
                </h1>
                <p className={`text-base ${darkMode ? 'text-slate-400' : 'text-slate-600'} max-w-xl leading-relaxed`}>
                  Upload a speech recording and select a world-class orator as your baseline. Oscine maps acoustic deviations to millisecond-precise flaw windows with causal mathematical explanations.
                </p>
              </div>
            </div>
          </motion.div>
        )}

        {/* ── SETUP PANEL ── */}
        <motion.div
          layout
          className={`rounded-3xl border ${darkMode ? 'border-white/8 bg-[#0d1220]/90' : 'border-slate-200 bg-white'} shadow-xl overflow-hidden`}
        >
          {/* Tab Bar */}
          <div className={`flex items-center justify-between px-6 py-4 border-b ${darkMode ? 'border-white/5 bg-white/[0.02]' : 'border-slate-100 bg-slate-50'}`}>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSelectUploadMode}
                className={`px-5 py-2.5 rounded-xl text-sm font-bold uppercase tracking-wider transition-all duration-200 flex items-center gap-2 ${activeTabMode === 'upload'
                  ? 'bg-gradient-to-r from-indigo-600 to-indigo-500 text-white shadow-lg shadow-indigo-500/30 scale-[1.02]'
                  : darkMode ? 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
              >
                <Upload className="w-4 h-4" />
                Upload Audio & Transcript
              </button>
              <button
                type="button"
                onClick={() => setActiveTabMode('preset')}
                className={`px-5 py-2.5 rounded-xl text-sm font-bold uppercase tracking-wider transition-all duration-200 flex items-center gap-2 ${activeTabMode === 'preset'
                  ? 'bg-gradient-to-r from-amber-600 to-orange-500 text-white shadow-lg shadow-amber-500/30 scale-[1.02]'
                  : darkMode ? 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
              >
                <Layers className="w-4 h-4" />
                Test Benchmark Presets
              </button>
            </div>
            <button
              type="button"
              onClick={() => setShowTranscriptDrawer(!showTranscriptDrawer)}
              className={`text-sm font-semibold flex items-center gap-2 px-4 py-2 rounded-xl border transition-all ${showTranscriptDrawer
                ? darkMode ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' : 'bg-indigo-50 text-indigo-600 border-indigo-200'
                : darkMode ? 'bg-white/5 text-slate-400 border-white/10 hover:text-white hover:border-white/20' : 'bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100'
                }`}
            >
              <Eye className="w-4 h-4" />
              {showTranscriptDrawer ? 'Hide Script' : 'View Script'}
              {showTranscriptDrawer ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>

          <div className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">

              {/* Reference Baseline Picker */}
              <div className="lg:col-span-3 space-y-2">
                <label className={`text-sm font-bold uppercase tracking-wider flex items-center gap-2 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  <Sliders className="w-4 h-4 text-indigo-500" />
                  Reference Baseline
                </label>
                <select
                  value={selectedRef || ''}
                  onChange={e => handleRefChange(e.target.value)}
                  className={`w-full p-3.5 rounded-xl border text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all ${!selectedRef
                    ? darkMode ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300' : 'bg-indigo-50 border-indigo-300 text-indigo-700'
                    : darkMode ? 'bg-white/5 border-white/10 text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-800'
                    }`}
                >
                  <option value="" disabled>— Select Speaker —</option>
                  {references.map(r => (
                    <option key={r.id} value={r.id}>{r.title} ({r.duration}s)</option>
                  ))}
                </select>
                {!selectedRef && (
                  <p className="text-xs text-indigo-400 flex items-center gap-1 mt-1">
                    <AlertTriangle className="w-3 h-3" /> Required before analysis
                  </p>
                )}
              </div>

              {/* Upload / Presets */}
              <div className="lg:col-span-6">
                <AnimatePresence mode="wait">
                  {activeTabMode === 'upload' ? (
                    <motion.div key="upload"
                      initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 10 }}
                      className="grid grid-cols-1 sm:grid-cols-2 gap-3"
                    >
                      {/* Audio Card */}
                      <div
                        onClick={() => audioInputRef.current?.click()}
                        className={`p-4 rounded-2xl border-2 border-dashed transition-all cursor-pointer group card-shine ${audioFile
                          ? darkMode ? 'border-indigo-500 bg-indigo-500/10' : 'border-indigo-400 bg-indigo-50'
                          : darkMode ? 'border-white/10 bg-white/[0.03] hover:border-indigo-500/50 hover:bg-indigo-500/5' : 'border-slate-200 bg-slate-50 hover:border-indigo-300 hover:bg-indigo-50/50'
                          }`}
                      >
                        <input ref={audioInputRef} type="file" accept="audio/*" onChange={handleAudioUpload} className="hidden" />
                        <div className="flex items-center gap-3">
                          <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 transition-all ${audioFile ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30' : darkMode ? 'bg-white/5 text-slate-500 group-hover:bg-indigo-500/20 group-hover:text-indigo-400' : 'bg-slate-200 text-slate-500 group-hover:text-indigo-500'
                            }`}>
                            {audioFile ? <Check className="w-5 h-5" /> : <FileAudio className="w-5 h-5" />}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-bold text-slate-700 dark:text-slate-200">Audio (.wav)</div>
                            <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                              {audioFile ? audioFile.name : 'Click to select file'}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Transcript Card */}
                      <div
                        onClick={() => transcriptInputRef.current?.click()}
                        className={`p-4 rounded-2xl border-2 border-dashed transition-all cursor-pointer group card-shine ${transcriptFile
                          ? darkMode ? 'border-emerald-500 bg-emerald-500/10' : 'border-emerald-400 bg-emerald-50'
                          : darkMode ? 'border-white/10 bg-white/[0.03] hover:border-emerald-500/50 hover:bg-emerald-500/5' : 'border-slate-200 bg-slate-50 hover:border-emerald-300 hover:bg-emerald-50/50'
                          }`}
                      >
                        <input ref={transcriptInputRef} type="file" accept=".txt,text/plain" onChange={handleTranscriptUpload} className="hidden" />
                        <div className="flex items-center gap-3">
                          <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 transition-all ${transcriptFile ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/30' : darkMode ? 'bg-white/5 text-slate-500 group-hover:bg-emerald-500/20 group-hover:text-emerald-400' : 'bg-slate-200 text-slate-500 group-hover:text-emerald-500'
                            }`}>
                            {transcriptFile ? <Check className="w-5 h-5" /> : <FileText className="w-5 h-5" />}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-bold text-slate-700 dark:text-slate-200">Transcript (.txt) <span className="text-xs font-normal text-slate-400">optional</span></div>
                            <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                              {transcriptFile ? transcriptFile.name : 'Optional — improves alignment'}
                            </p>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ) : (
                    <motion.div key="presets"
                      initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }}
                    >
                      <div className="space-y-4">
                        {PRESET_GROUPS.map(({ key, group, subtitle, icon: Icon, emoji, gradient, glow, activeBg, badge, items }) => (
                          <div key={group} className="space-y-2">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2.5">
                                <div className={`w-7 h-7 rounded-lg bg-gradient-to-tr ${gradient} text-white shadow-md ${glow} flex items-center justify-center shrink-0`}>
                                  <Icon className="w-4 h-4 drop-shadow-sm" />
                                </div>
                                <span className="font-extrabold text-sm text-slate-800 dark:text-slate-100 tracking-tight">
                                  {group}
                                </span>
                                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${badge} border hidden sm:inline-flex items-center gap-1`}>
                                  <span>{emoji}</span> {subtitle}
                                </span>
                              </div>
                            </div>
                            <div className="grid grid-cols-3 gap-2.5">
                              {items.map(flaw => {
                                const sev = flaw.split('_').pop();
                                const isSelected = selectedPresetName === flaw;
                                return (
                                  <button
                                    key={flaw}
                                    type="button"
                                    onClick={() => handleSelectPreset(flaw)}
                                    className={`py-2 px-3 text-sm rounded-xl border font-bold transition-all hover-lift relative overflow-hidden text-center ${isSelected
                                      ? `${activeBg} shadow-md scale-[1.02]`
                                      : darkMode
                                        ? 'border-white/8 bg-white/[0.03] text-slate-300 hover:border-white/20 hover:text-white hover:bg-white/5'
                                        : 'border-slate-200 bg-white/80 text-slate-700 hover:border-indigo-200 hover:bg-white hover:shadow-sm'
                                      }`}
                                  >
                                    <span className={`block text-[11px] font-semibold uppercase tracking-wider ${isSelected ? 'opacity-80' : 'text-slate-400'}`}>
                                      {SEVERITY_LABELS[sev]}
                                    </span>
                                    <span className="text-sm font-extrabold">{sev}</span>
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Run Analysis */}
              <div className="lg:col-span-3 flex flex-col gap-3">
                <button
                  type="button"
                  onClick={handleAnalyze}
                  disabled={isAnalyzing || !audioFile || !selectedRef}
                  className={`relative w-full h-14 font-bold rounded-2xl text-base shadow-xl transition-all duration-200 overflow-hidden flex items-center justify-center gap-3 ${isAnalyzing || !audioFile || !selectedRef
                    ? 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-indigo-600 via-violet-600 to-indigo-600 text-white shadow-indigo-500/30 hover:shadow-indigo-500/50 hover:scale-[1.02] active:scale-[0.98] cursor-pointer'
                    }`}
                >
                  {isAnalyzing ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full spin-3d" />
                      <span className="animate-pulse">Computing DSP…</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      Run Analysis
                    </>
                  )}
                  {/* Animated gradient sweep */}
                  {!isAnalyzing && audioFile && selectedRef && (
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full hover:translate-x-full transition-transform duration-700" />
                  )}
                </button>

                {/* Progress bar */}
                {isAnalyzing && (
                  <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400"
                      animate={{ width: `${analyzeProgress}%` }}
                      transition={{ ease: 'easeOut' }}
                    />
                  </div>
                )}

                {/* Active file status */}
                {audioFile && (
                  <div className={`text-xs rounded-xl px-3 py-2 border flex items-center gap-2 ${darkMode ? 'border-white/8 bg-white/[0.03] text-slate-400' : 'border-slate-200 bg-slate-50 text-slate-500'}`}>
                    <Mic className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                    <span className="truncate font-medium">{audioFile.name}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Script Drawer */}
            <AnimatePresence>
              {showTranscriptDrawer && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-5 pt-4 border-t border-white/5"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-indigo-500" />
                      <span className="text-sm font-bold text-slate-700 dark:text-slate-200">Active Speech Script</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-mono ${darkMode ? 'bg-white/5 text-slate-400' : 'bg-slate-100 text-slate-500'}`}>
                        {transcriptFile ? 'Custom Upload' : `Baseline (${selectedRef || '—'})`}
                      </span>
                    </div>
                    <span className="text-xs font-mono text-slate-400">{wordCount} words</span>
                  </div>
                  <div className={`p-4 rounded-2xl border text-sm leading-relaxed max-h-44 overflow-y-auto ${darkMode ? 'bg-white/[0.03] border-white/8 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'}`}>
                    {activeTranscriptText || "No transcript available."}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Compared against footer */}
            {selectedRef && (
              <div className={`mt-4 pt-3 border-t ${darkMode ? 'border-white/5' : 'border-slate-100'} flex items-center justify-end text-xs text-slate-500`}>
                Compared against: <span className={`ml-1.5 font-semibold ${darkMode ? 'text-indigo-400' : 'text-indigo-600'}`}>{selectedRef}</span>
              </div>
            )}
          </div>
        </motion.div>

        {/* ── RESULTS ── */}
        <AnimatePresence>
          {result && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">

              {/* Scorecard — Ring style */}
              <div className={`p-6 rounded-3xl border ${darkMode ? 'border-white/8 bg-[#0d1220]/90' : 'border-slate-200 bg-white'} shadow-xl`}>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                  <div>
                    <h2 className="text-lg font-black text-slate-800 dark:text-slate-100">Evaluative Rubric Scores</h2>
                    <p className="text-sm text-slate-500 mt-0.5">Deterministic acoustic deviation scoring</p>
                  </div>
                  <div className="flex items-center gap-4">
                    <button
                      onClick={exportDiagnosticReport}
                      className={`px-3.5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 border shadow-sm transition-all hover:scale-105 active:scale-95 ${darkMode
                        ? 'border-indigo-500/40 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20'
                        : 'border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
                        }`}
                      title="Download complete diagnostic report (JSON)"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Export Diagnostic Report</span>
                    </button>
                    <div className="text-right">
                      <div className="text-4xl font-black gradient-text">{result.scores.overall_score.toFixed(1)}</div>
                      <div className="text-sm text-slate-500">/ 10 composite</div>
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap justify-around gap-6">
                  <ScoreRing value={result.scores.pacing_score} label="Pacing Cadence" icon={Zap} emoji="⚡" />
                  <ScoreRing value={result.scores.pauses_score} label="Pause Continuity" icon={Timer} emoji="⏱️" />
                  <ScoreRing value={result.scores.volume_score} label="Volume Stability" icon={Volume2} emoji="🔊" />
                  <ScoreRing value={result.scores.expressiveness_score} label="Pitch Expressiveness" icon={Activity} emoji="📉" />
                  {result.text_alignment_ratio !== undefined && (
                    <div className="flex flex-col items-center gap-2">
                      <div className={`w-20 h-20 rounded-2xl border-2 ${darkMode ? 'border-cyan-500/30 bg-cyan-500/10' : 'border-cyan-400/30 bg-cyan-50'} flex flex-col items-center justify-center`}>
                        <span className="text-xl font-black text-cyan-500">{(result.text_alignment_ratio * 100).toFixed(0)}%</span>
                        <span className="text-[9px] text-slate-400 font-medium">Alignment</span>
                      </div>
                      <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 text-center">Text Similarity</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Waveform */}
              <div className={`p-6 rounded-3xl border ${darkMode ? 'border-white/8 bg-[#0d1220]/90' : 'border-slate-200 bg-white'} shadow-xl`}>
                <div className="flex justify-between items-center mb-4">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => wavesurfer.current?.playPause()}
                      className="w-11 h-11 rounded-full bg-gradient-to-tr from-indigo-600 to-violet-600 hover:shadow-lg hover:shadow-indigo-500/30 text-white flex items-center justify-center transition-all hover:scale-105 active:scale-95"
                    >
                      {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                    </button>
                    <div>
                      <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">Temporal Prosody Waveform</h3>
                      <span className="text-xs text-slate-400 font-mono">{currentTime.toFixed(2)}s / {result.duration}s</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-sm font-semibold text-rose-500 bg-rose-500/10 px-4 py-2 rounded-xl border border-rose-500/20">
                    <AlertTriangle className="w-4 h-4" />
                    Red regions = Flaw windows
                  </div>
                </div>
                <div ref={waveformRef} className={`rounded-2xl p-3 ${darkMode ? 'bg-white/[0.03]' : 'bg-slate-50'}`} />
              </div>

              {/* Multi-track charts */}
              <div className={`p-6 rounded-3xl border ${darkMode ? 'border-white/8 bg-[#0d1220]/90' : 'border-slate-200 bg-white'} shadow-xl space-y-4`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BarChart2 className="w-5 h-5 text-indigo-500" />
                    <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">Multi-Track Prosodic Dynamics</h3>
                  </div>
                  <span className="text-sm text-slate-400">Crosshair cursor synchronized across tracks</span>
                </div>
                {[
                  { ref: chartRefPitch, title: 'Fundamental Frequency (F₀ Semitone / Z-Score)', refKey: 'f0', partKey: 'f0', yName: 'Pitch (z)' },
                  { ref: chartRefRate, title: 'Speech Cadence (Words Per Second)', refKey: 'rate', partKey: 'rate', yName: 'wps' },
                  { ref: chartRefPause, title: 'Pre-Word Pause Length (Seconds of Silence)', refKey: 'pause', partKey: 'pause', yName: 'Seconds' },
                ].map(({ ref, title, refKey, partKey, yName }) => (
                  <div key={title} className={`p-3 rounded-2xl border ${darkMode ? 'border-white/5 bg-white/[0.02]' : 'border-slate-100 bg-slate-50'}`}>
                    <ReactECharts
                      ref={ref}
                      option={makeChartOption(
                        title,
                        result.series.ref.t.map((t, i) => [t, result.series.ref[refKey][i]]),
                        result.series.part.t.map((t, i) => [t, result.series.part[partKey][i]]),
                        yName, result.regions
                      )}
                      style={{ height: 150 }}
                    />
                  </div>
                ))}
              </div>

              {/* Causal Report */}
              <div className={`p-6 rounded-3xl border ${darkMode ? 'border-white/8 bg-[#0d1220]/90' : 'border-slate-200 bg-white'} shadow-xl`}>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                  <div>
                    <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">Causal Anomaly Diagnostic Report</h3>
                    <p className="text-sm text-slate-500 mt-0.5">Numeric breakdowns of detected acoustic deviations</p>
                  </div>
                  <div className={`flex p-1 rounded-2xl border gap-1 overflow-x-auto ${darkMode ? 'border-white/8 bg-white/[0.03]' : 'border-slate-200 bg-slate-100'}`}>
                    {[
                      { id: "all", label: "All Anomalies", emoji: "✨" },
                      { id: "pause", label: "Pauses", emoji: "⏱️" },
                      { id: "rushed", label: "Pacing", emoji: "⚡" },
                      { id: "monotone", label: "Pitch", emoji: "📉" },
                      { id: "volume", label: "Volume", emoji: "🔊" }
                    ].map(tab => (
                      <button
                        key={tab.id}
                        onClick={() => setFilterCategory(tab.id)}
                        className={`px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-1.5 transition-all ${filterCategory === tab.id
                          ? darkMode ? 'bg-indigo-600 text-white shadow-sm' : 'bg-white text-indigo-600 shadow-sm border border-slate-200/80'
                          : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                          }`}
                      >
                        <span>{tab.emoji}</span>
                        <span>{tab.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {filteredRegions.length === 0 ? (
                  <div className="p-10 text-center border-2 border-dashed rounded-2xl border-emerald-500/30 bg-emerald-500/5">
                    <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
                    <p className="text-base font-bold text-emerald-500">Zero Critical Deviations Detected</p>
                    <p className="text-sm text-slate-400 mt-1">Delivery follows baseline prosodic contours within tolerance.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <AnimatePresence>
                      {filteredRegions.map((reg, i) => {
                        const flawKey = getFlawKey(reg.dimension);
                        const cfg = DIMENSION_CONFIG[flawKey] || DIMENSION_CONFIG.errant_pause;
                        const FlawIcon = cfg.icon;
                        return (
                          <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.04 }}
                            className={`p-5 rounded-2xl border transition-all hover-lift card-shine ${darkMode ? 'border-white/8 bg-white/[0.03] hover:bg-white/[0.05]' : 'border-slate-200 bg-white hover:border-indigo-300 hover:shadow-lg'
                              }`}
                          >
                            <div className="flex items-start justify-between gap-3 mb-3">
                              <div className="flex items-center gap-3">
                                <div className={`w-9 h-9 rounded-xl bg-gradient-to-tr ${cfg.gradient} text-white shadow-md ${cfg.glow} flex items-center justify-center shrink-0`}>
                                  <FlawIcon className="w-5 h-5 drop-shadow-sm" />
                                </div>
                                <div>
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-sm font-extrabold text-slate-800 dark:text-slate-100 capitalize">
                                      {reg.dimension.replace(/_/g, ' ')}
                                    </span>
                                    <span className="text-sm">{cfg.emoji}</span>
                                  </div>
                                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${cfg.badge} border ${cfg.border} inline-block mt-0.5`}>
                                    {cfg.subtitle}
                                  </span>
                                </div>
                              </div>
                              <span className="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-white/5 px-2.5 py-1 rounded-lg shrink-0">
                                {reg.start}s – {reg.end}s
                              </span>
                            </div>
                            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{reg.explanation}</p>
                            <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 dark:border-white/5">
                              <div className={`text-xs font-mono font-extrabold ${cfg.text} flex items-center gap-1.5`}>
                                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                                +{reg.peak_z}σ acoustic deviation
                              </div>
                              <button
                                onClick={() => jumpToTime(reg.start, reg.end)}
                                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all hover:scale-105 active:scale-95 ${darkMode ? 'bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30' : 'bg-indigo-50 text-indigo-600 hover:bg-indigo-100 shadow-sm'
                                  }`}
                              >
                                <Volume2 className="w-3.5 h-3.5" /> Play Segment
                              </button>
                            </div>
                          </motion.div>
                        );
                      })}
                    </AnimatePresence>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── FOOTER CARDS ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className={`p-6 rounded-3xl border shadow-sm card-shine ${darkMode ? 'border-white/8 bg-[#0d1220]/70 text-slate-300' : 'border-slate-200 bg-white text-slate-600'}`}>
            <h4 className="font-bold text-base text-slate-800 dark:text-slate-100 flex items-center gap-2.5 mb-3">
              <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                <ShieldCheck className="w-4 h-4 text-indigo-500" />
              </div>
              Objective Prosodic Normalization
            </h4>
            <p className="text-sm leading-relaxed text-slate-500 dark:text-slate-400">
              Oscine extracts acoustic features with <span className="text-indigo-400 font-medium">pYIN</span> and <span className="text-indigo-400 font-medium">Faster-Whisper</span>, computing file-specific Z-scores to ensure evaluation remains independent of speaker gender, vocal timbre, or biological pitch range.
            </p>
          </div>
          <div className={`p-6 rounded-3xl border shadow-sm card-shine ${darkMode ? 'border-white/8 bg-[#0d1220]/70 text-slate-300' : 'border-slate-200 bg-white text-slate-600'}`}>
            <h4 className="font-bold text-base text-amber-600 dark:text-amber-400 flex items-center gap-2.5 mb-3">
              <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
              </div>
              Educational & Advisory Notice
            </h4>
            <p className="text-sm leading-relaxed text-slate-500 dark:text-slate-400">
              This application serves as an objective acoustic coaching aid. Numeric outputs reflect statistical variance relative to a target reference baseline and do not represent subjective appraisals of rhetoric or communication authority.
            </p>
          </div>
        </div>

      </main>
    </div>
  );
}