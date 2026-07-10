import { useState } from 'react';
import { 
  ShieldCheck, MessageSquareCode, FileText, 
  Upload, Sparkles, FileImage, Music, History
} from 'lucide-react';
import { api } from '../lib/api';

interface CitizenPortalProps {
  setSuccessMsg: (msg: string | null) => void;
  setErrorMsg: (msg: string | null) => void;
  loading: boolean;
  setLoading: (l: boolean) => void;
}

export function CitizenPortal({ setSuccessMsg, setErrorMsg, loading, setLoading }: CitizenPortalProps) {
  const [activeTab, setActiveTab] = useState<'text' | 'currency' | 'audio'>('text');
  
  // Text state
  const [reporterName, setReporterName] = useState('');
  const [phoneInput, setPhoneInput] = useState('');
  const [transcriptInput, setTranscriptInput] = useState('');
  const [textVerdict, setTextVerdict] = useState<{ score: number; explanation: string } | null>(null);

  // Currency state
  const [currencyFile, setCurrencyFile] = useState<File | null>(null);
  const [currencyVerdict, setCurrencyVerdict] = useState<{
    id: number;
    verdict: string;
    confidence: number;
    features: Record<string, any>;
  } | null>(null);

  // Audio state
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioVerdict, setAudioVerdict] = useState<{
    verdict: string;
    confidence: number;
    reason: string;
    features: {
      zero_crossing_rate: number;
      rms_energy: number;
      hf_energy_ratio: number;
      duration_seconds: number;
    };
  } | null>(null);

  // History list containing all submissions
  const [submissionHistory, setSubmissionHistory] = useState<Array<{
    id: string | number;
    type: 'Text Complaint' | 'Banknote Scan' | 'Audio Deepfake';
    timestamp: string;
    status: string;
    verdict: string;
    score: number;
  }>>([
    { id: 'S-9912', type: 'Text Complaint', timestamp: '2026-07-09 18:24', status: 'Reviewed', verdict: 'High Scam Risk', score: 85 },
    { id: 'S-9908', type: 'Banknote Scan', timestamp: '2026-07-09 14:10', status: 'Completed', verdict: 'Real Note', score: 98 },
  ]);

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transcriptInput.trim()) return;

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    setTextVerdict(null);

    try {
      // Simulate random coordinates around Delhi
      const lat = 28.5 + Math.random() * 0.18;
      const lng = 77.1 + Math.random() * 0.18;

      const complaint = await api.submitComplaint({
        reporter_name: reporterName || "Anonymous",
        phone: phoneInput || null,
        text_content: transcriptInput,
        location_lat: lat,
        location_lng: lng
      });

      setSuccessMsg("Scam report successfully submitted to the Public Safety Intelligence registry.");
      
      // Request detailed risk scoring
      await api.checkRisk(complaint.id);
      const details = await api.getComplaint(complaint.id);
      
      setTextVerdict({
        score: details.risk_score,
        explanation: details.risk_explanation || "No explanation provided by AI."
      });

      // Add to local audit history
      setSubmissionHistory(prev => [
        {
          id: `C-${complaint.id}`,
          type: 'Text Complaint',
          timestamp: new Date().toISOString().replace('T', ' ').substring(0, 16),
          status: 'Analyzed',
          verdict: details.risk_score >= 60 ? 'Scam Threat' : 'Low Risk',
          score: details.risk_score
        },
        ...prev
      ]);

      setTranscriptInput('');
    } catch (e: any) {
      console.error(e);
      setErrorMsg("Failed to connect or submit to the security registry.");
    } finally {
      setLoading(false);
    }
  };

  const handleCurrencySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currencyFile) return;

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    setCurrencyVerdict(null);

    try {
      const result = await api.scanCounterfeit(currencyFile);
      setCurrencyVerdict(result);
      setSuccessMsg("Banknote scanned successfully. Check the AI features extraction below.");

      setSubmissionHistory(prev => [
        {
          id: `N-${result.id}`,
          type: 'Banknote Scan',
          timestamp: new Date().toISOString().replace('T', ' ').substring(0, 16),
          status: 'Completed',
          verdict: result.verdict,
          score: Math.round(result.confidence)
        },
        ...prev
      ]);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to process currency scan.");
    } finally {
      setLoading(false);
    }
  };

  const handleAudioSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!audioFile) return;

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    setAudioVerdict(null);

    try {
      const result = await api.checkSpeech(audioFile);
      setAudioVerdict(result);
      setSuccessMsg("Speech audio analysis completed successfully.");

      setSubmissionHistory(prev => [
        {
          id: `A-${Math.floor(Math.random() * 900) + 100}`,
          type: 'Audio Deepfake',
          timestamp: new Date().toISOString().replace('T', ' ').substring(0, 16),
          status: 'Completed',
          verdict: result.verdict === 'Deepfake' ? 'Synthetic/Clone' : 'Authentic',
          score: Math.round(result.confidence)
        },
        ...prev
      ]);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to analyze audio sample. Ensure it is a valid WAV, MP3, or M4A file.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto w-full">
      {/* Warm and Reassuring Hero Card */}
      <div className="bg-gradient-to-r from-emerald-950/80 to-teal-900/60 rounded-3xl p-6 md:p-8 border border-emerald-500/20 shadow-xl">
        <div className="flex items-center gap-4 mb-3">
          <div className="p-3 bg-emerald-500/20 text-emerald-300 rounded-2xl flex items-center justify-center">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-xl md:text-2xl font-bold text-white tracking-tight">Citizen Security Hub</h2>
            <p className="text-sm text-emerald-300/80 font-medium">Empowering public vigilance with unified AI threat scoring</p>
          </div>
        </div>
        <p className="text-xs md:text-sm text-slate-350 leading-relaxed max-w-2xl">
          RakshaNet protects citizens by analyzing potential cyber frauds instantly. Report suspect caller transcripts, audit suspicious banknotes for counterfeit signatures, or test recorded call snippets for deepfake audio modifications.
        </p>
      </div>

      {/* Audit Tool Tabs */}
      <div className="flex border-b border-slate-800">
        <button
          onClick={() => setActiveTab('text')}
          className={`flex items-center gap-2 px-6 py-3.5 text-xs uppercase tracking-wider font-bold transition-all border-b-2 ${
            activeTab === 'text'
              ? 'border-emerald-500 text-emerald-400 bg-slate-900/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-4.5 h-4.5" /> Suspect Call Transcript
        </button>
        <button
          onClick={() => setActiveTab('currency')}
          className={`flex items-center gap-2 px-6 py-3.5 text-xs uppercase tracking-wider font-bold transition-all border-b-2 ${
            activeTab === 'currency'
              ? 'border-emerald-500 text-emerald-400 bg-slate-900/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileImage className="w-4.5 h-4.5" /> Counterfeit Note Scanner
        </button>
        <button
          onClick={() => setActiveTab('audio')}
          className={`flex items-center gap-2 px-6 py-3.5 text-xs uppercase tracking-wider font-bold transition-all border-b-2 ${
            activeTab === 'audio'
              ? 'border-emerald-500 text-emerald-400 bg-slate-900/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Music className="w-4.5 h-4.5" /> Deepfake Audio Auditor
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Audit Form Column */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* TAB 1: TEXT TRANSCRIPT COMPLAINT */}
          {activeTab === 'text' && (
            <div className="glass-panel rounded-2xl p-6 space-y-6">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <MessageSquareCode className="w-5 h-5 text-emerald-400" /> Verify Call Transcript
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Did a caller claim to be an official or threaten legal arrest? Paste what they said below to obtain an immediate AI risk assessment.
                </p>
              </div>

              <form onSubmit={handleTextSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1.5 tracking-wider">Reporter Name (Optional)</label>
                    <input 
                      type="text" 
                      value={reporterName}
                      onChange={(e) => setReporterName(e.target.value)}
                      placeholder="e.g. John Doe"
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500" 
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1.5 tracking-wider">Caller Phone Entity (Optional)</label>
                    <input 
                      type="text" 
                      value={phoneInput}
                      onChange={(e) => setPhoneInput(e.target.value)}
                      placeholder="e.g. +91 9998887776"
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500" 
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1.5 tracking-wider">Transcribed Message Details</label>
                  <textarea 
                    rows={4}
                    value={transcriptInput}
                    onChange={(e) => setTranscriptInput(e.target.value)}
                    placeholder="e.g. I am calling from Delhi Customs. A contraband parcel in your name was intercepted..."
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                    minLength={5}
                    required
                  />
                </div>

                <button 
                  type="submit" 
                  disabled={loading}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 transition-colors text-white font-bold text-xs uppercase tracking-wider rounded-xl py-3 flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-emerald-950/40"
                >
                  {loading ? (
                    <>
                      <Sparkles className="w-4.5 h-4.5 animate-spin" /> Analyzing Threat Signal...
                    </>
                  ) : "Analyze Transcript"}
                </button>
              </form>

              {/* Text Assessment Result */}
              {textVerdict && (
                <div className={`p-5 rounded-2xl border transition-all ${
                  textVerdict.score >= 60 ? 'border-red-500/30 bg-red-950/15' : 'border-slate-800 bg-slate-900/30'
                }`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-bold text-white text-sm">Instant Safety Verdict</h4>
                      <p className="text-[10px] text-slate-400">Scored via sentence-transformers NLP engine</p>
                    </div>
                    <div className="text-right">
                      <span className={`text-xl font-black ${
                        textVerdict.score >= 70 ? 'text-red-400' : textVerdict.score >= 40 ? 'text-amber-400' : 'text-emerald-400'
                      }`}>
                        {textVerdict.score}%
                      </span>
                      <p className="text-[9px] uppercase font-bold text-slate-500">Threat Risk</p>
                    </div>
                  </div>

                  <div className="mt-4 p-4 bg-slate-950/60 rounded-xl border border-slate-900">
                    <p className="text-xs font-semibold text-slate-200 mb-1">AI Classification Explanation:</p>
                    <p className="text-xs text-slate-450 leading-relaxed">{textVerdict.explanation}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: COUNTERFEIT CURRENCY SCAN */}
          {activeTab === 'currency' && (
            <div className="glass-panel rounded-2xl p-6 space-y-6">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <FileImage className="w-5 h-5 text-emerald-400" /> Counterfeit Note Scanner
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Upload a high-quality picture of a currency banknote. The model processes OpenCV HSV color profile checks against reserve parameters.
                </p>
              </div>

              <form onSubmit={handleCurrencySubmit} className="space-y-4">
                <div className="border-2 border-dashed border-slate-850 rounded-2xl p-6 flex flex-col items-center justify-center text-center bg-slate-900/10">
                  <Upload className="w-10 h-10 text-slate-500 mb-3" />
                  <input
                    type="file"
                    accept="image/*"
                    id="currency-file-upload"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setCurrencyFile(e.target.files[0]);
                      }
                    }}
                  />
                  <label htmlFor="currency-file-upload" className="cursor-pointer bg-slate-900 border border-slate-800 text-slate-300 font-semibold px-4 py-2 rounded-xl text-xs hover:bg-slate-850 transition-colors">
                    {currencyFile ? currencyFile.name : "Select Banknote Image"}
                  </label>
                  <p className="text-[10px] text-slate-500 mt-2">JPEG, PNG files are processed. Max size 5MB.</p>
                </div>

                <button 
                  type="submit" 
                  disabled={loading || !currencyFile}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 transition-colors text-white font-bold text-xs uppercase tracking-wider rounded-xl py-3 flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-emerald-950/40"
                >
                  {loading ? (
                    <>
                      <Sparkles className="w-4.5 h-4.5 animate-spin" /> Running CV Histogram Audit...
                    </>
                  ) : "Scan Note Integrity"}
                </button>
              </form>

              {/* Currency scan result */}
              {currencyVerdict && (
                <div className={`p-5 rounded-2xl border transition-all ${
                  currencyVerdict.verdict === 'Counterfeit' ? 'border-red-500/30 bg-red-950/15' : 'border-emerald-500/20 bg-emerald-950/10'
                }`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-bold text-white text-sm">Computer Vision Scan Result</h4>
                      <p className="text-[10px] text-slate-400">Database reference record ID: #{currencyVerdict.id}</p>
                    </div>
                    <div className="text-right">
                      <span className={`text-sm font-bold uppercase px-3 py-1 rounded-full ${
                        currencyVerdict.verdict === 'Counterfeit' ? 'bg-red-950 text-red-400 border border-red-900/50' : 'bg-emerald-950 text-emerald-400 border border-emerald-900/50'
                      }`}>
                        {currencyVerdict.verdict}
                      </span>
                      <p className="text-[10px] font-semibold text-slate-400 mt-2">Confidence: {currencyVerdict.confidence}%</p>
                    </div>
                  </div>

                  {currencyVerdict.features && (
                    <div className="mt-4 p-4 bg-slate-950/60 rounded-xl border border-slate-900">
                      <p className="text-xs font-semibold text-slate-200 mb-2">Extracted Feature Histograms:</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[10px]">
                        {Object.entries(currencyVerdict.features).map(([key, val]) => (
                          <div key={key} className="bg-slate-900/50 p-2.5 rounded-lg border border-slate-900">
                            <span className="text-slate-500 block uppercase">{key.replace(/_/g, ' ')}</span>
                            <span className="font-semibold text-slate-350 mt-1 block">
                              {typeof val === 'number' ? val.toFixed(2) : String(val)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: AUDIO DEEPFAKE AUDIT */}
          {activeTab === 'audio' && (
            <div className="glass-panel rounded-2xl p-6 space-y-6">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Music className="w-5 h-5 text-emerald-400" /> Deepfake Audio Check
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Upload an audio file (WAV, MP3, or M4A) of a suspicious voicemail or voice snippet. The model calculates Zero Crossing Rate and high frequency vocoder ratios.
                </p>
              </div>

              <form onSubmit={handleAudioSubmit} className="space-y-4">
                <div className="border-2 border-dashed border-slate-850 rounded-2xl p-6 flex flex-col items-center justify-center text-center bg-slate-900/10">
                  <Upload className="w-10 h-10 text-slate-500 mb-3" />
                  <input
                    type="file"
                    accept="audio/*"
                    id="audio-file-upload"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setAudioFile(e.target.files[0]);
                      }
                    }}
                  />
                  <label htmlFor="audio-file-upload" className="cursor-pointer bg-slate-900 border border-slate-800 text-slate-300 font-semibold px-4 py-2 rounded-xl text-xs hover:bg-slate-850 transition-colors">
                    {audioFile ? audioFile.name : "Select Voice Audio File"}
                  </label>
                  <p className="text-[10px] text-slate-500 mt-2">WAV, MP3, or M4A format supported. Max size 8MB.</p>
                </div>

                <button 
                  type="submit" 
                  disabled={loading || !audioFile}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 transition-colors text-white font-bold text-xs uppercase tracking-wider rounded-xl py-3 flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-emerald-950/40"
                >
                  {loading ? (
                    <>
                      <Sparkles className="w-4.5 h-4.5 animate-spin" /> Extracting Spectral Features...
                    </>
                  ) : "Check Spectral Verdict"}
                </button>
              </form>

              {/* Audio check result */}
              {audioVerdict && (
                <div className={`p-5 rounded-2xl border transition-all ${
                  audioVerdict.verdict === 'Deepfake' ? 'border-red-500/30 bg-red-950/15' : 'border-emerald-500/20 bg-emerald-950/10'
                }`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-bold text-white text-sm">Acoustic Analysis Completed</h4>
                      <p className="text-[10px] text-slate-400 mt-1">{audioVerdict.reason}</p>
                    </div>
                    <div className="text-right">
                      <span className={`text-sm font-bold uppercase px-3 py-1 rounded-full ${
                        audioVerdict.verdict === 'Deepfake' ? 'bg-red-950 text-red-400 border border-red-900/50' : 'bg-emerald-950 text-emerald-400 border border-emerald-900/50'
                      }`}>
                        {audioVerdict.verdict}
                      </span>
                      <p className="text-[10px] font-semibold text-slate-400 mt-2">Confidence: {audioVerdict.confidence}%</p>
                    </div>
                  </div>

                  {audioVerdict.features && (
                    <div className="mt-4 p-4 bg-slate-950/60 rounded-xl border border-slate-900">
                      <p className="text-xs font-semibold text-slate-200 mb-2">Acoustic Signatures Evaluated:</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[10px]">
                        <div className="bg-slate-900/50 p-2.5 rounded-lg border border-slate-900">
                          <span className="text-slate-500 block uppercase">Zero Crossing Rate</span>
                          <span className="font-semibold text-slate-350 mt-1 block">{audioVerdict.features.zero_crossing_rate.toFixed(4)}</span>
                        </div>
                        <div className="bg-slate-900/50 p-2.5 rounded-lg border border-slate-900">
                          <span className="text-slate-500 block uppercase">RMS Energy</span>
                          <span className="font-semibold text-slate-350 mt-1 block">{audioVerdict.features.rms_energy.toFixed(4)}</span>
                        </div>
                        <div className="bg-slate-900/50 p-2.5 rounded-lg border border-slate-900">
                          <span className="text-slate-500 block uppercase">HF Energy Ratio</span>
                          <span className="font-semibold text-slate-350 mt-1 block">{audioVerdict.features.hf_energy_ratio.toFixed(4)}</span>
                        </div>
                        <div className="bg-slate-900/50 p-2.5 rounded-lg border border-slate-900">
                          <span className="text-slate-500 block uppercase">Duration</span>
                          <span className="font-semibold text-slate-350 mt-1 block">{audioVerdict.features.duration_seconds}s</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

        </div>

        {/* History Column */}
        <div className="lg:col-span-1">
          <div className="glass-panel rounded-2xl p-4 flex flex-col h-[550px] overflow-hidden">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 pb-3 border-b border-slate-850 flex items-center gap-1.5">
              <History className="w-4 h-4 text-emerald-400" /> Your Safety Audits
            </h3>
            
            <div className="flex-1 overflow-y-auto mt-3 space-y-3 pr-1">
              {submissionHistory.map((item, idx) => (
                <div key={idx} className="p-3 rounded-xl border border-slate-850 bg-slate-900/20 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-200">{item.type}</span>
                    <span className="text-[9px] text-slate-500">{item.timestamp}</span>
                  </div>
                  <div className="flex items-center justify-between mt-2.5">
                    <span className="text-[10px] text-slate-450">ID: {item.id}</span>
                    <span className={`text-[10px] font-bold ${
                      item.verdict.includes('Scam') || item.verdict === 'Counterfeit' || item.verdict === 'Synthetic/Clone'
                        ? 'text-red-400' 
                        : 'text-emerald-400'
                    }`}>
                      {item.verdict} ({item.score}%)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
export default CitizenPortal;
