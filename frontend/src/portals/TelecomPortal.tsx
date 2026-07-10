import { useState } from 'react';
import { PhoneCall, Check, ShieldAlert, Radio, Activity, Search, ArrowRight } from 'lucide-react';
import { api } from '../lib/api';

interface TelecomPortalProps {
  setSuccessMsg: (msg: string | null) => void;
  setErrorMsg: (msg: string | null) => void;
  loading: boolean;
  setLoading: (l: boolean) => void;
}

export function TelecomPortal({ setSuccessMsg, setErrorMsg, loading, setLoading }: TelecomPortalProps) {
  const [callsList] = useState([
    { id: 1, caller: "+91 9998887776", callee: "+91 9876543210", duration: "2m 14s", risk: 80, location: "Delhi, DL" },
    { id: 2, caller: "+91 9898989898", callee: "+91 9123456789", duration: "0m 45s", risk: 15, location: "Gurugram, HR" },
    { id: 3, caller: "+91 8887776665", callee: "+91 9555444333", duration: "5m 30s", risk: 90, location: "Noida, UP" },
    { id: 4, caller: "+91 7001234567", callee: "+91 8223344556", duration: "1m 10s", risk: 42, location: "Delhi, DL" }
  ]);

  const [searchQuery, setSearchQuery] = useState('');
  const [flaggedCalls, setFlaggedCalls] = useState<number[]>([]);

  const handleFlagCall = async (callId: number, callerPhone: string) => {
    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await api.submitComplaint({
        reporter_name: "Telecom Intercept Service",
        phone: callerPhone,
        text_content: "This is police calling. Connect to Skype immediately. You are under digital arrest for tax evasion.",
        location_lat: 28.55,
        location_lng: 77.15
      });
      
      setFlaggedCalls(prev => [...prev, callId]);
      setSuccessMsg(`Call logs and intercept transcripts for number ${callerPhone} forwarded to police case file.`);
    } catch (e: any) {
      console.error(e);
      setErrorMsg("Failed to forward intercept logs to police gateway.");
    } finally {
      setLoading(false);
    }
  };

  const filteredCalls = callsList.filter(c => 
    c.caller.includes(searchQuery) || 
    c.callee.includes(searchQuery) ||
    c.location.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <PhoneCall className="w-5.5 h-5.5 text-red-500 animate-pulse" /> Live Telecommunication Intercepts
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time parsing of GSM protocols. Call signals are analyzed for spoofing markers, matching IMSI records, and deepfake voice signatures.
          </p>
        </div>
        
        {/* Streaming indicator */}
        <div className="flex items-center gap-2 bg-red-950/30 border border-red-900/40 px-3.5 py-1.5 rounded-xl">
          <Radio className="w-4 h-4 text-red-500 animate-ping" />
          <span className="text-[10px] uppercase font-black tracking-wider text-red-400">TELECOM LIVE STREAM</span>
        </div>
      </div>

      {/* Search filters */}
      <div className="relative max-w-md">
        <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-500" />
        <input 
          type="text" 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter caller, callee or location..."
          className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-red-500"
        />
      </div>

      {/* Grid listing call cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredCalls.map((call) => {
          const isFlagged = flaggedCalls.includes(call.id);
          return (
            <div 
              key={call.id}
              className={`p-4 rounded-2xl border transition-all ${
                call.risk >= 75
                  ? 'border-red-500/20 bg-red-950/5 hover:border-red-500/40' 
                  : 'border-slate-850 bg-slate-900/10 hover:border-slate-800'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Active Channel ID: #{call.id}</span>
                  <div className="flex items-center gap-1.5 mt-1">
                    <div className={`w-1.5 h-1.5 rounded-full ${call.risk >= 75 ? 'bg-red-500 animate-pulse' : 'bg-amber-500'}`} />
                    <span className="font-mono text-xs font-semibold text-slate-250">{call.caller}</span>
                  </div>
                </div>

                <div className="text-right">
                  <span className={`text-xs font-bold ${call.risk >= 75 ? 'text-red-400' : 'text-amber-400'}`}>
                    {call.risk}% Risk
                  </span>
                  <p className="text-[8px] text-slate-550 mt-1 uppercase font-semibold">Spoof Probability</p>
                </div>
              </div>

              {/* Call connection trace visualization */}
              <div className="my-4 bg-slate-950 p-3 rounded-xl border border-slate-900 text-[10px] space-y-2">
                <div className="flex items-center justify-between text-slate-500 font-mono text-[9px]">
                  <span>Origin: {call.location}</span>
                  <span>Duration: {call.duration}</span>
                </div>
                <div className="flex items-center justify-between text-slate-350 font-semibold border-t border-slate-900 pt-2 font-mono">
                  <span>Routing Destination</span>
                  <div className="flex items-center gap-1">
                    <ArrowRight className="w-3 h-3 text-slate-500" />
                    <span>{call.callee}</span>
                  </div>
                </div>
              </div>

              {/* Call flagging buttons */}
              <div className="flex justify-end">
                {isFlagged ? (
                  <div className="flex items-center gap-1 bg-emerald-950/40 text-emerald-400 border border-emerald-900/50 px-3.5 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-wider">
                    <Check className="w-3.5 h-3.5" /> Intercept Sent
                  </div>
                ) : (
                  <button 
                    onClick={() => handleFlagCall(call.id, call.caller)}
                    disabled={loading}
                    className="bg-red-950 hover:bg-red-900/80 text-red-400 border border-red-900/30 text-[10px] font-black uppercase tracking-wider px-3.5 py-2 rounded-xl transition-all cursor-pointer flex items-center gap-1.5"
                  >
                    <ShieldAlert className="w-3.5 h-3.5" /> Flag Call Script
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Signal processing visualization widget */}
      <div className="p-4 bg-slate-950/40 rounded-xl border border-slate-850">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-350 mb-3 flex items-center gap-1.5">
          <Activity className="w-4.5 h-4.5 text-blue-500" /> Telephony Signal Diagnostics
        </h3>
        <div className="h-10 flex items-end gap-1.5 pr-2 select-none overflow-hidden">
          {Array.from({ length: 48 }).map((_, i) => {
            const h = 20 + Math.sin(i * 0.4) * 15 + Math.random() * 8;
            return (
              <div 
                key={i} 
                className="flex-1 bg-slate-800/80 rounded-t hover:bg-red-500/50 transition-colors"
                style={{ height: `${h}px` }} 
              />
            );
          })}
        </div>
      </div>

    </div>
  );
}
export default TelecomPortal;
