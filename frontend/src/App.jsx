import React, { useState, useEffect, useRef } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Play, Pause, Upload, CheckCircle2, AlertTriangle, 
  BarChart2, Sun, Moon, Volume2, ShieldCheck, 
  Sparkles, Layers, Sliders, FileAudio, FileText, Check, ChevronDown, ChevronUp, Eye
} from 'lucide-react';

const API_BASE = "http://localhost:8000";

export default function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [references, setReferences] = useState([]);
  const [selectedRef, setSelectedRef] = useState("speech_01");

  // Selection states
  const [activeTabMode, setActiveTabMode] = useState("upload");
  const [audioFile, setAudioFile] = useState(null);
  const [transcriptFile, setTranscriptFile] = useState(null);
  const [activeTranscriptText, setActiveTranscriptText] = useState("");
  const [showTranscriptDrawer, setShowTranscriptDrawer] = useState(false);
  const [selectedPresetName, setSelectedPresetName] = useState(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [filterCategory, setFilterCategory] = useState("all");

  // Audio / WaveSurfer refs
  const waveformRef = useRef(null);
  const wavesurfer = useRef(null);
  const regionsPlugin = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  // Synchronized chart refs
  const chartRefPitch = useRef(null);
  const chartRefRate = useRef(null);
  const chartRefPause = useRef(null);

  // Hidden file inputs
  const audioInputRef = useRef(null);
  const transcriptInputRef = useRef(null);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  useEffect(() => {
    fetch(`${API_BASE}/api/references`)
      .then(res => res.json())
      .then(data => {
        setReferences(data);
        if (data.length > 0) {
          setSelectedRef(data[0].id);
          setActiveTranscriptText(data[0].transcript || "");
        }
      })
      .catch(err => console.error("Error fetching baseline models:", err));
  }, []);

  const handleRefChange = (refId) => {
    setSelectedRef(refId);
    const chosen = references.find(r => r.id === refId);
    if (chosen && chosen.transcript && !transcriptFile) {
      setActiveTranscriptText(chosen.transcript);
    }
  };

  const initWaveform = (audioUrl, flawRegions = []) => {
    if (wavesurfer.current) {
      wavesurfer.current.destroy();
    }

    const ws = WaveSurfer.create({
      container: waveformRef.current,
      waveColor: darkMode ? '#6366f1' : '#818cf8',
      progressColor: darkMode ? '#a5b4fc' : '#4f46e5',
      cursorColor: darkMode ? '#f8fafc' : '#0f172a',
      cursorWidth: 2,
      height: 90,
      barWidth: 3,
      barGap: 3,
      barRadius: 3,
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
          color: darkMode ? 'rgba(244, 63, 94, 0.35)' : 'rgba(244, 63, 94, 0.25)',
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
  };

  const handleSelectPreset = async (flawName) => {
    setActiveTabMode("preset");
    setSelectedPresetName(flawName);
    try {
      const url = `${API_BASE}/api/audio/${selectedRef}/${flawName}.wav`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("Could not find file on server.");
      const blob = await res.blob();
      const file = new File([blob], `${flawName}.wav`, { type: 'audio/wav' });
      setAudioFile(file);
      setTranscriptFile(null);

      // Re-link baseline transcript for this preset
      const chosen = references.find(r => r.id === selectedRef);
      if (chosen && chosen.transcript) {
        setActiveTranscriptText(chosen.transcript);
      }
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
      reader.onload = (event) => {
        setActiveTranscriptText(event.target.result);
      };
      reader.readAsText(file);
    }
  };

  const handleAnalyze = async () => {
    if (!audioFile) {
      alert("Please upload a .wav audio file or pick a benchmark preset first.");
      return;
    }

    setIsAnalyzing(true);
    const formData = new FormData();
    formData.append("reference_id", selectedRef);
    formData.append("audio", audioFile);
    if (activeTranscriptText.trim()) {
      formData.append("transcript", activeTranscriptText.trim());
    }

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Analysis failed.");
      }

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

  const jumpToTime = (start, end) => {
    if (!wavesurfer.current) return;
    wavesurfer.current.seekTo(start / wavesurfer.current.getDuration());
    wavesurfer.current.play();
  };

  const makeChartOption = (title, refData, partData, yName, regions) => {
    const textColor = darkMode ? '#94a3b8' : '#64748b';
    const splitLineColor = darkMode ? '#1e293b' : '#f1f5f9';

    const markAreas = regions.map(r => ([
      { xAxis: r.start, itemStyle: { color: darkMode ? 'rgba(244, 63, 94, 0.2)' : 'rgba(244, 63, 94, 0.12)' } },
      { xAxis: r.end }
    ]));

    return {
      title: { text: title, textStyle: { color: textColor, fontSize: 11, fontWeight: 600 } },
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', lineStyle: { color: '#f43f5e', type: 'dashed' } },
        backgroundColor: darkMode ? '#131b2a' : '#ffffff',
        borderColor: darkMode ? '#1e293b' : '#e2e8f0',
        textStyle: { color: darkMode ? '#f8fafc' : '#0f172a', fontSize: 11 }
      },
      legend: {
        data: ['Ideal Reference', 'Participant'],
        textStyle: { color: textColor, fontSize: 10 },
        right: 0,
        top: 0
      },
      grid: { left: 45, right: 15, top: 26, bottom: 22 },
      xAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: splitLineColor } },
        splitLine: { show: false },
        axisLabel: { color: textColor, fontSize: 9, formatter: '{value}s' }
      },
      yAxis: {
        type: 'value',
        name: yName,
        nameTextStyle: { color: textColor, fontSize: 9 },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: splitLineColor } },
        axisLabel: { color: textColor, fontSize: 9 }
      },
      series: [
        {
          name: 'Ideal Reference',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: refData,
          lineStyle: { width: 2, color: '#4f46e5' },
          markArea: { silent: true, data: markAreas }
        },
        {
          name: 'Participant',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: partData,
          lineStyle: { width: 2, color: '#d97706', type: 'dashed' }
        }
      ]
    };
  };

  const filteredRegions = result?.regions.filter(r => {
    if (filterCategory === "all") return true;
    return r.dimension.includes(filterCategory);
  }) || [];

  const wordCount = activeTranscriptText.trim() ? activeTranscriptText.trim().split(/\s+/).length : 0;

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-darkBg text-slate-100' : 'bg-slate-50 text-slate-800'} transition-colors duration-300 font-sans pb-16`}>
      {/* Top Navbar */}
      <nav className={`border-b ${darkMode ? 'border-darkBorder bg-darkSurface/80' : 'border-slate-200 bg-white/80'} sticky top-0 z-50 glass-panel`}>
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold tracking-tight text-lg">Oscine</span>
              <span className="text-[10px] ml-2 px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-semibold uppercase">Prosody Engine</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setDarkMode(!darkMode)}
              className={`p-2 rounded-lg border transition ${darkMode ? 'border-darkBorder bg-darkSurface text-amber-400 hover:bg-slate-800' : 'border-slate-200 bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
              title="Toggle Light/Dark Theme"
            >
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <div className="hidden sm:flex items-center gap-2 text-xs font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              FastAPI Core Online
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 pt-8 space-y-6">
        {/* Setup Ribbon */}
        <div className={`p-6 rounded-2xl border ${darkMode ? 'border-darkBorder bg-darkSurface/50' : 'border-slate-200 bg-white'} shadow-sm transition-all`}>
          
          {/* Mode Switch Tabs */}
          <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-100 dark:border-darkBorder">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSelectUploadMode}
                className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition ${
                  activeTabMode === 'upload'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : darkMode ? 'bg-darkBg text-slate-400 hover:text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                1. Upload Audio & Transcript 
              </button>

              <button
                type="button"
                onClick={() => { setActiveTabMode('preset'); }}
                className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition ${
                  activeTabMode === 'preset'
                    ? 'bg-amber-600 text-white shadow-md'
                    : darkMode ? 'bg-darkBg text-slate-400 hover:text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                2. Test Benchmark Presets 
              </button>
            </div>

            <button
              type="button"
              onClick={() => setShowTranscriptDrawer(!showTranscriptDrawer)}
              className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline flex items-center gap-1.5 cursor-pointer bg-indigo-50 dark:bg-indigo-950/50 px-3 py-1.5 rounded-lg border border-indigo-200 dark:border-indigo-900"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>{showTranscriptDrawer ? 'Hide Script' : 'View Script'}</span>
              {showTranscriptDrawer ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-center">
            
            {/* Step 1: Target Baseline Dropdown */}
            <div className="lg:col-span-3 space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-indigo-500" /> Reference Baseline
              </label>
              <select
                value={selectedRef}
                onChange={e => handleRefChange(e.target.value)}
                className={`w-full p-3 rounded-xl border text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${darkMode ? 'bg-darkBg border-darkBorder text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-800'}`}
              >
                {references.map(r => (
                  <option key={r.id} value={r.id}>{r.title} ({r.duration}s)</option>
                ))}
              </select>
            </div>

            {/* Step 2: Upload Drop-Cards OR Preset Selector */}
            <div className="lg:col-span-6">
              {activeTabMode === 'upload' ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  
                  {/* Card A: Audio Upload */}
                  <div
                    onClick={() => audioInputRef.current?.click()}
                    className={`p-3.5 rounded-xl border border-dashed transition cursor-pointer flex items-center gap-3 group ${
                      audioFile 
                        ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/40' 
                        : darkMode 
                          ? 'border-darkBorder bg-darkBg/60 hover:border-indigo-400' 
                          : 'border-slate-300 bg-slate-50/70 hover:border-indigo-500'
                    }`}
                  >
                    <input
                      ref={audioInputRef}
                      type="file"
                      accept="audio/*"
                      onChange={handleAudioUpload}
                      className="hidden"
                    />
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                      audioFile ? 'bg-indigo-600 text-white' : 'bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400 group-hover:text-indigo-500'
                    }`}>
                      <FileAudio className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200 truncate">Audio (.wav)</span>
                        {audioFile && <Check className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />}
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
                        {audioFile ? audioFile.name : "Select participant file"}
                      </p>
                    </div>
                  </div>

                  {/* Card B: Transcript Upload */}
                  <div
                    onClick={() => transcriptInputRef.current?.click()}
                    className={`p-3.5 rounded-xl border border-dashed transition cursor-pointer flex items-center gap-3 group ${
                      transcriptFile 
                        ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/40' 
                        : darkMode 
                          ? 'border-darkBorder bg-darkBg/60 hover:border-emerald-400' 
                          : 'border-slate-300 bg-slate-50/70 hover:border-emerald-500'
                    }`}
                  >
                    <input
                      ref={transcriptInputRef}
                      type="file"
                      accept=".txt,text/plain"
                      onChange={handleTranscriptUpload}
                      className="hidden"
                    />
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                      transcriptFile ? 'bg-emerald-600 text-white' : 'bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400 group-hover:text-emerald-500'
                    }`}>
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200 truncate">Transcript (.txt)</span>
                        {transcriptFile && <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />}
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
                        {transcriptFile ? transcriptFile.name : "Optional custom .txt"}
                      </p>
                    </div>
                  </div>

                </div>
              ) : (
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-amber-500 flex items-center gap-1.5 mb-1.5">
                    <Layers className="w-3.5 h-3.5 text-amber-500" /> Choose Preset Flaw to Test
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {["flawed_pause_L1", "flawed_pause_L2", "flawed_pause_L3", "flawed_rushed_L1", "flawed_rushed_L2", "flawed_rushed_L3"].map((flaw) => {
                      const isSelected = selectedPresetName === flaw;
                      const label = flaw.replace("flawed_", "").replace("_", " ").toUpperCase();
                      return (
                        <button
                          key={flaw}
                          type="button"
                          onClick={() => handleSelectPreset(flaw)}
                          className={`py-2 text-xs rounded-lg border font-medium transition ${
                            isSelected
                              ? 'border-amber-500 bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 font-bold ring-2 ring-amber-500/20'
                              : darkMode ? 'border-darkBorder bg-darkBg hover:border-slate-600' : 'border-slate-200 bg-slate-50 hover:border-slate-300'
                          }`}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Step 3: Run Analysis Button */}
            <div className="lg:col-span-3">
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={isAnalyzing || !audioFile}
                className="w-full h-12 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-600 disabled:opacity-40 text-white font-bold rounded-xl shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 transition cursor-pointer"
              >
                {isAnalyzing ? (
                  <span className="text-xs uppercase tracking-wider animate-pulse">Computing DSP...</span>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span className="text-sm">Run Analysis</span>
                  </>
                )}
              </button>
            </div>

          </div>

          {/* Collapsible Script Inspector Drawer */}
          {showTranscriptDrawer && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-5 pt-4 border-t border-slate-100 dark:border-darkBorder/60"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 text-indigo-500" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">
                    Active Speech Script
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 font-mono">
                    {transcriptFile ? 'Source: Custom Upload' : `Source: Baseline (${selectedRef})`}
                  </span>
                </div>
                <span className="text-xs font-mono text-slate-400">
                  {wordCount} words
                </span>
              </div>
              <div className={`p-4 rounded-xl border text-xs leading-relaxed max-h-40 overflow-y-auto ${
                darkMode ? 'bg-darkBg/90 border-darkBorder text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'
              }`}>
                {activeTranscriptText || "No transcript available for this selection."}
              </div>
            </motion.div>
          )}

          {/* Active File Banner */}
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-darkBorder/60 flex items-center justify-between text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <FileAudio className="w-4 h-4 text-indigo-500" />
              <span>Target Audio:</span>
              <strong className="text-slate-800 dark:text-slate-200">
                {audioFile ? audioFile.name : "None selected (Choose an audio file)"}
              </strong>
            </div>
            <div className="text-[11px] text-slate-400">
              Compared against: <span className="font-semibold text-slate-700 dark:text-slate-200">{selectedRef}</span>
            </div>
          </div>
        </div>

        {/* Results Area */}
        <AnimatePresence>
          {result && (
            <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
              
              {/* Scorecard Strip */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {[
                  { label: "Pacing Cadence", val: result.scores.pacing_score },
                  { label: "Pause Continuity", val: result.scores.pauses_score },
                  { label: "Volume Stability", val: result.scores.volume_score },
                  { label: "Pitch Expressiveness", val: result.scores.expressiveness_score },
                ].map((item, idx) => (
                  <div key={idx} className={`p-4 rounded-xl border ${darkMode ? 'border-darkBorder bg-darkSurface' : 'border-slate-200 bg-white'} shadow-sm`}>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{item.label}</span>
                    <div className="flex items-baseline gap-2 mt-1">
                      <span className="text-2xl font-black">{item.val.toFixed(1)}</span>
                      <span className="text-xs text-slate-400">/ 10</span>
                    </div>
                    <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full mt-3 overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-700 ${item.val >= 8 ? 'bg-emerald-500' : item.val >= 6 ? 'bg-indigo-500' : 'bg-rose-500'}`} 
                        style={{ width: `${item.val * 10}%` }}
                      />
                    </div>
                  </div>
                ))}

                <div className="col-span-2 md:col-span-1 p-4 rounded-xl border border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 via-transparent to-transparent flex flex-col justify-between">
                  <div className="flex justify-between items-center">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">Composite</span>
                    {result.text_alignment_ratio !== undefined && (
                      <span className="text-[10px] bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded font-mono">
                        {(result.text_alignment_ratio * 100).toFixed(0)}% Text Sim
                      </span>
                    )}
                  </div>
                  <div className="my-1">
                    <span className="text-3xl font-black text-indigo-600 dark:text-indigo-400">{result.scores.overall_score.toFixed(1)}</span>
                    <span className="text-xs text-slate-400"> / 10.0</span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-medium">Deterministic Rubric Output</span>
                </div>
              </div>

              {/* Master Waveform Inspector */}
              <div className={`p-6 rounded-2xl border ${darkMode ? 'border-darkBorder bg-darkSurface' : 'border-slate-200 bg-white'} shadow-sm`}>
                <div className="flex justify-between items-center mb-4">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => wavesurfer.current?.playPause()}
                      className="w-10 h-10 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center transition shadow-md"
                    >
                      {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                    </button>
                    <div>
                      <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">Temporal Prosody Waveform</h3>
                      <span className="text-xs text-slate-400">{currentTime.toFixed(2)}s / {result.duration}s</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-medium text-rose-500 bg-rose-500/10 px-3 py-1.5 rounded-lg border border-rose-500/20">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Red Shading Indicates Flaw Windows</span>
                  </div>
                </div>

                <div ref={waveformRef} className={`rounded-xl p-2 ${darkMode ? 'bg-darkBg' : 'bg-slate-50'}`} />
              </div>

              {/* Synchronized Acoustic Contours */}
              <div className={`p-6 rounded-2xl border ${darkMode ? 'border-darkBorder bg-darkSurface' : 'border-slate-200 bg-white'} shadow-sm space-y-4`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BarChart2 className="w-4 h-4 text-indigo-500" />
                    <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">Multi-Track Prosodic Dynamics</h3>
                  </div>
                  <span className="text-xs text-slate-400">Crosshair cursor synchronized across tracks</span>
                </div>

                <div className="space-y-3">
                  <div className={`p-2 rounded-xl border ${darkMode ? 'border-darkBorder/60 bg-darkBg/60' : 'border-slate-100 bg-slate-50'}`}>
                    <ReactECharts
                      ref={chartRefPitch}
                      option={makeChartOption(
                        'Fundamental Frequency ($F_0$ Semitone / Z-Score)',
                        result.series.ref.t.map((t, i) => [t, result.series.ref.f0[i]]),
                        result.series.part.t.map((t, i) => [t, result.series.part.f0[i]]),
                        'Pitch (z)', result.regions
                      )}
                      style={{ height: 140 }}
                    />
                  </div>

                  <div className={`p-2 rounded-xl border ${darkMode ? 'border-darkBorder/60 bg-darkBg/60' : 'border-slate-100 bg-slate-50'}`}>
                    <ReactECharts
                      ref={chartRefRate}
                      option={makeChartOption(
                        'Speech Cadence (Words Per Second)',
                        result.series.ref.t.map((t, i) => [t, result.series.ref.rate[i]]),
                        result.series.part.t.map((t, i) => [t, result.series.part.rate[i]]),
                        'wps', result.regions
                      )}
                      style={{ height: 140 }}
                    />
                  </div>

                  <div className={`p-2 rounded-xl border ${darkMode ? 'border-darkBorder/60 bg-darkBg/60' : 'border-slate-100 bg-slate-50'}`}>
                    <ReactECharts
                      ref={chartRefPause}
                      option={makeChartOption(
                        'Pre-Word Pause Length (Seconds of Silence)',
                        result.series.ref.t.map((t, i) => [t, result.series.ref.pause[i]]),
                        result.series.part.t.map((t, i) => [t, result.series.part.pause[i]]),
                        'Seconds', result.regions
                      )}
                      style={{ height: 140 }}
                    />
                  </div>
                </div>
              </div>

              {/* Explanations & Segment Inspector */}
              <div className={`p-6 rounded-2xl border ${darkMode ? 'border-darkBorder bg-darkSurface' : 'border-slate-200 bg-white'} shadow-sm`}>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
                  <div>
                    <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">Causal Anomaly Diagnostic Report</h3>
                    <p className="text-xs text-slate-400 mt-0.5">Numeric breakdowns of detected acoustic deviations</p>
                  </div>
                  
                  <div className={`flex p-1 rounded-xl border text-xs ${darkMode ? 'border-darkBorder bg-darkBg' : 'border-slate-200 bg-slate-100'}`}>
                    {["all", "pause", "rushed", "monotone", "vocal_clarity"].map(tab => (
                      <button
                        key={tab}
                        onClick={() => setFilterCategory(tab)}
                        className={`px-3 py-1 rounded-lg font-medium capitalize transition ${filterCategory === tab ? (darkMode ? 'bg-darkSurface text-indigo-400' : 'bg-white text-indigo-600 shadow-sm') : 'text-slate-400 hover:text-slate-600'}`}
                      >
                        {tab.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>

                {filteredRegions.length === 0 ? (
                  <div className="p-8 text-center border border-dashed rounded-xl border-emerald-500/30 bg-emerald-500/5">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                    <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">Zero Critical Deviations Detected</p>
                    <p className="text-xs text-slate-400 mt-1">Delivery follows baseline prosodic contours within tolerance.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filteredRegions.map((reg, i) => (
                      <div key={i} className={`p-4 rounded-xl border transition hover:shadow-md ${darkMode ? 'border-darkBorder bg-darkBg/50 hover:border-slate-700' : 'border-slate-200 bg-slate-50/50 hover:border-slate-300'}`}>
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-500 border border-rose-500/20 uppercase tracking-wider">
                            {reg.dimension.replace('_', ' ')}
                          </span>
                          <span className="text-xs font-mono text-slate-400 font-semibold">{reg.start}s – {reg.end}s</span>
                        </div>
                        <p className="text-xs text-slate-600 dark:text-slate-300 mt-2.5 leading-relaxed">{reg.explanation}</p>
                        <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-200 dark:border-darkBorder">
                          <span className="text-[11px] font-mono text-slate-400">Deviation: +{reg.peak_z}σ</span>
                          <button
                            onClick={() => jumpToTime(reg.start, reg.end)}
                            className="px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
                          >
                            <Volume2 className="w-3.5 h-3.5" /> Play Segment
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

            </motion.div>
          )}
        </AnimatePresence>

        {/* 2 Standalone Footer Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
          <div className={`p-5 rounded-2xl border shadow-sm transition-all ${
            darkMode 
              ? 'border-darkBorder bg-darkSurface/60 text-slate-300' 
              : 'border-slate-200/90 bg-white text-slate-600'
          }`}>
            <h4 className="font-bold text-sm text-slate-800 dark:text-slate-100 flex items-center gap-2 mb-2">
              <ShieldCheck className="w-4 h-4 text-indigo-500 shrink-0" /> Objective Prosodic Normalization
            </h4>
            <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Oscine extracts acoustic features with pYIN and Faster-Whisper, computing file-specific Z-scores to ensure evaluation remains independent of speaker gender, vocal timbre, or biological pitch range.
            </p>
          </div>

          <div className={`p-5 rounded-2xl border shadow-sm transition-all ${
            darkMode 
              ? 'border-darkBorder bg-darkSurface/60 text-slate-300' 
              : 'border-slate-200/90 bg-white text-slate-600'
          }`}>
            <h4 className="font-bold text-sm text-amber-600 dark:text-amber-400 flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" /> Educational & Advisory Notice
            </h4>
            <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              This application serves as an objective acoustic coaching aid. Numeric outputs reflect statistical variance relative to a target reference baseline and do not represent subjective appraisals of rhetoric or communication authority.
            </p>
          </div>
        </div>

      </main>
    </div>
  );
}