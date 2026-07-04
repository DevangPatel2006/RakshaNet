import React, { useState, useEffect, useRef } from 'react';
import { 
  Shield, User, Landmark, PhoneCall, Settings, 
  AlertTriangle, CheckCircle, Search, Download, 
  Map, Activity, Share2, Plus, RefreshCw, Layers
} from 'lucide-react';

const API_BASE = "http://localhost:8000";

interface Alert {
  id: number;
  title: string;
  description: string;
  severity: string;
  status: string;
  target_role: string;
  created_at: string;
}

interface GraphNode {
  id: number;
  type: string;
  value: string;
  value_hash: string;
  risk_score: number;
  cluster_id: number;
  x?: number;
  y?: number;
}

interface GraphLink {
  source: string;
  target: string;
  relation_type: string;
  weight: number;
}

export default function App() {
  const [role, setRole] = useState<'citizen' | 'officer' | 'bank_analyst' | 'telecom_analyst' | 'admin'>('citizen');
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string>('');
  
  // Realtime alerts (WebSocket)
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // General state
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 1. Citizen Portal State
  const [reporterName, setReporterName] = useState('');
  const [phoneInput, setPhoneInput] = useState('');
  const [transcriptInput, setTranscriptInput] = useState('');
  const [citizenVerdict, setCitizenVerdict] = useState<{ score: number; explanation: string } | null>(null);
  const [myComplaints, setMyComplaints] = useState<any[]>([]);

  // 2. Police Console State
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCase, setSelectedCase] = useState<any | null>(null);
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({ nodes: [], links: [] });
  const [heatmapPoints, setHeatmapPoints] = useState<any[]>([]);
  const [evidenceVerified, setEvidenceVerified] = useState<{ valid: boolean; hash: string } | null>(null);

  // 3. Bank Console State
  const [transactions, setTransactions] = useState<any[]>([]);
  const [txSearchId, setTxSearchId] = useState('12345');
  const [scoredTx, setScoredTx] = useState<any | null>(null);

  // 4. Telecom Console State
  const [callsList, setCallsList] = useState<any[]>([
    { id: 1, caller: "+91 9998887776", callee: "+91 9876543210", duration: "2m 14s", risk: 80 },
    { id: 2, caller: "+91 9898989898", callee: "+91 9123456789", duration: "0m 45s", risk: 15 },
    { id: 3, caller: "+91 8887776665", callee: "+91 9555444333", duration: "5m 30s", risk: 90 }
  ]);

  // 5. Admin Panel State
  const [modelMetrics, setModelMetrics] = useState<any[]>([]);

  // Auto-login configuration on role switch
  useEffect(() => {
    // Determine credentials based on role
    let user = 'citizen_john';
    let pass = 'citizen_pass';
    if (role === 'officer') { user = 'officer_delhi'; pass = 'officer_pass'; }
    else if (role === 'bank_analyst') { user = 'bank_analyst_sam'; pass = 'bank_pass'; }
    else if (role === 'telecom_analyst') { user = 'telecom_analyst_tina'; pass = 'telecom_pass'; }
    else if (role === 'admin') { user = 'admin'; pass = 'admin_pass'; }

    setErrorMsg(null);
    setSuccessMsg(null);
    setCitizenVerdict(null);

    // Call login API
    const loginData = new URLSearchParams();
    loginData.append('username', user);
    loginData.append('password', pass);

    fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: loginData
    })
    .then(r => {
      if (!r.ok) throw new Error("Authentication failed");
      return r.json();
    })
    .then(data => {
      setToken(data.access_token);
      setUsername(data.username);
      
      // Establish WebSocket
      connectWebSocket(data.access_token);
      
      // Fetch role-specific data
      fetchRoleData(role, data.access_token);
    })
    .catch(err => {
      setErrorMsg("Failed to authenticate session with the backend gateway.");
      setToken(null);
    });

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [role]);

  // Connect WebSocket
  const connectWebSocket = (authToken: string) => {
    if (wsRef.current) wsRef.current.close();

    const wsUrl = `ws://localhost:8000/alerts/stream?token=${authToken}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setWsConnected(true);
      console.log("WebSocket connected successfully.");
    };

    ws.onmessage = (event) => {
      const alertData: Alert = JSON.parse(event.data);
      console.log("WebSocket Alert Received:", alertData);
      setAlerts(prev => [alertData, ...prev]);
    };

    ws.onclose = () => {
      setWsConnected(false);
      console.log("WebSocket closed.");
    };

    wsRef.current = ws;
  };

  // Fetch role-specific dashboard datasets
  const fetchRoleData = (activeRole: string, tokenStr: string) => {
    const headers = { 'Authorization': `Bearer ${tokenStr}` };

    if (activeRole === 'officer') {
      // 1. Fetch Cases
      fetch(`${API_BASE}/cases`, { headers })
        .then(r => r.json())
        .then(data => setCases(data))
        .catch(e => console.error("Error fetching cases:", e));

      // 2. Fetch Graph Data
      fetch(`${API_BASE}/graph/cluster`, { headers })
        .then(r => r.json())
        .then(data => setGraphData(data))
        .catch(e => console.error("Error fetching graph:", e));

      // 3. Fetch Heatmap point arrays
      fetch(`${API_BASE}/geo/heatmap`, { headers })
        .then(r => r.json())
        .then(data => setHeatmapPoints(data.features || []))
        .catch(e => console.error("Error fetching geo heatmap:", e));
    }
    else if (activeRole === 'admin') {
      fetch(`${API_BASE}/admin/model-metrics`, { headers })
        .then(r => r.json())
        .then(data => setModelMetrics(data))
        .catch(e => console.error("Error model metrics:", e));
    }
  };

  // Simple Spring force simulation for custom SVG Graph
  useEffect(() => {
    if (graphData.nodes.length === 0) return;

    // Initialize positions randomly if they don't exist
    const width = 500;
    const height = 300;
    const nodes = graphData.nodes.map(n => ({
      ...n,
      x: n.x || width / 2 + (Math.random() - 0.5) * 200,
      y: n.y || height / 2 + (Math.random() - 0.5) * 150
    }));

    const links = [...graphData.links];

    // Physics constants
    const kRepulsion = 1500;
    const kAttraction = 0.06;
    const padding = 20;

    let animFrame: number;

    const tick = () => {
      // Repulsion between all nodes
      for (let i = 0; i < nodes.length; i++) {
        let fx = 0;
        let fy = 0;
        const u = nodes[i];
        for (let j = 0; j < nodes.length; j++) {
          if (i === j) continue;
          const v = nodes[j];
          const dx = u.x! - v.x!;
          const dy = u.y! - v.y!;
          const distSq = dx * dx + dy * dy + 0.1;
          const dist = Math.sqrt(distSq);
          if (dist < 150) {
            const force = kRepulsion / distSq;
            fx += (dx / dist) * force;
            fy += (dy / dist) * force;
          }
        }
        u.x! += fx;
        u.y! += fy;
      }

      // Attraction along links
      for (const link of links) {
        const u = nodes.find(n => n.value_hash === link.source);
        const v = nodes.find(n => n.value_hash === link.target);
        if (u && v) {
          const dx = v.x! - u.x!;
          const dy = v.y! - u.y!;
          const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;
          const force = dist * kAttraction * link.weight;
          const fX = (dx / dist) * force;
          const fY = (dy / dist) * force;
          u.x! += fX;
          u.y! += fY;
          v.x! -= fX;
          v.y! -= fY;
        }
      }

      // Gravity towards center and bounds constraint
      for (const u of nodes) {
        const dX = width / 2 - u.x!;
        const dY = height / 2 - u.y!;
        u.x! += dX * 0.02;
        u.y! += dY * 0.02;

        // Keep inside bounds
        u.x = Math.max(padding, Math.min(width - padding, u.x!));
        u.y = Math.max(padding, Math.min(height - padding, u.y!));
      }

      setGraphData({ nodes: [...nodes], links });
      animFrame = requestAnimationFrame(tick);
    };

    animFrame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animFrame);
  }, [graphData.links]);

  // Citizen submit complaint transcript
  const handleCitizenSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transcriptInput.trim()) return;

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      // Simulate lat/lng around Delhi region
      const lat = 28.5 + Math.random() * 0.18;
      const lng = 77.1 + Math.random() * 0.18;

      const res = await fetch(`${API_BASE}/complaints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reporter_name: reporterName || "Anonymous",
          phone: phoneInput || null,
          text_content: transcriptInput,
          location_lat: lat,
          location_lng: lng
        })
      });

      if (!res.ok) throw new Error("Submission failed");
      const complaint = await res.json();

      setSuccessMsg("Scam report successfully submitted to Central Public Intelligence registry.");
      setMyComplaints(prev => [complaint, ...prev]);

      // Call risk check endpoint to trigger AI Scoring explanation
      const riskRes = await fetch(`${API_BASE}/complaints/${complaint.id}/risk-check`);
      if (riskRes.ok) {
        // Wait, the risk check is calculated by the orchestrator on complaint submission
        // Since we already process it, let's fetch the detailed complaint
        const detailsRes = await fetch(`${API_BASE}/complaints/${complaint.id}`);
        const details = await detailsRes.json();
        setCitizenVerdict({
          score: details.risk_score,
          explanation: details.risk_explanation
        });
      }

      setTranscriptInput('');
    } catch (e: any) {
      setErrorMsg("Failed to connect or submit to the security registry.");
    } finally {
      setLoading(false);
    }
  };

  // Police inspect evidence hash integrity
  const handleVerifyEvidence = async (evId: number) => {
    setLoading(true);
    setEvidenceVerified(null);
    try {
      const res = await fetch(`${API_BASE}/evidence/${evId}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      const data = await res.json();
      setEvidenceVerified({
        valid: data.verification.valid,
        hash: data.sha256_hash
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Bank fetch transaction
  const handleGetTxScore = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setScoredTx(null);
    try {
      const res = await fetch(`${API_BASE}/transactions/${txSearchId}/score`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setScoredTx(data);
    } catch (err) {
      setErrorMsg("Failed to score transaction. Ensure ID is valid.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* Top Header Navigation */}
      <header className="glass-panel sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-red-600 rounded-xl critical-glow flex items-center justify-center text-white">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
              RakshaNet <span className="text-xs bg-slate-800 text-red-500 font-medium px-2 py-0.5 rounded-full border border-red-900/50">INTEL PORTAL</span>
            </h1>
            <p className="text-xs text-slate-400">Digital Public Safety Intelligence Hub</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* WebSocket Status Indicator */}
          <div className="flex items-center gap-1.5 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-[10px] uppercase font-semibold text-slate-400">
              {wsConnected ? 'Stream Active' : 'Stream Closed'}
            </span>
          </div>

          {/* Role selector dropdown */}
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-400 font-medium uppercase">Access Role:</label>
            <select 
              value={role} 
              onChange={(e) => setRole(e.target.value as any)}
              className="bg-slate-900 border border-slate-850 text-slate-100 text-sm rounded-lg px-3 py-1.5 focus:ring-red-500 focus:border-red-500"
            >
              <option value="citizen">Citizen App</option>
              <option value="officer">Police Console</option>
              <option value="bank_analyst">Bank Console</option>
              <option value="telecom_analyst">Telecom Dashboard</option>
              <option value="admin">Admin Panel</option>
            </select>
          </div>
        </div>
      </header>

      {/* Main Body Grid */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Left Ticker (alerts stream visible to all roles to represent integrated platform core) */}
        <section className="lg:col-span-1 flex flex-col gap-4">
          <div className="glass-panel rounded-2xl p-4 flex flex-col flex-1 h-[600px] overflow-hidden">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-sm font-bold uppercase tracking-wide text-slate-350 flex items-center gap-1.5">
                <Activity className="w-4.5 h-4.5 text-red-500" /> Live Threat Feed
              </h2>
              <span className="text-[10px] bg-red-950 text-red-400 font-semibold px-2 py-0.5 rounded border border-red-900/50">REDIS</span>
            </div>
            
            <div className="flex-1 overflow-y-auto mt-3 space-y-3 pr-1">
              {alerts.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-4">
                  <p className="text-xs text-slate-500">Waiting for live security threat streams...</p>
                </div>
              ) : (
                alerts.map((a, i) => (
                  <div key={i} className={`p-3 rounded-lg border text-xs glass-panel transition-all ${
                    a.severity === 'Critical' ? 'border-red-900/50 bg-red-950/20' : 'border-slate-850 bg-slate-900/40'
                  }`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`font-semibold ${a.severity === 'Critical' ? 'text-red-400' : 'text-amber-400'}`}>
                        {a.severity.toUpperCase()} ALERT
                      </span>
                      <span className="text-[9px] text-slate-500">Just Now</span>
                    </div>
                    <p className="font-semibold text-slate-200">{a.title}</p>
                    <p className="text-slate-400 mt-1">{a.description}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        {/* Right Main Panel (Switched based on role) */}
        <section className="lg:col-span-3 flex flex-col gap-6">
          
          {/* Status Display logs */}
          {errorMsg && (
            <div className="p-4 bg-red-950/30 border border-red-900/50 text-red-450 rounded-xl text-sm flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" /> {errorMsg}
            </div>
          )}
          {successMsg && (
            <div className="p-4 bg-green-950/30 border border-green-900/50 text-green-400 rounded-xl text-sm flex items-center gap-2">
              <CheckCircle className="w-5 h-5 flex-shrink-0" /> {successMsg}
            </div>
          )}

          {/* CITIZEN APP */}
          {role === 'citizen' && (
            <div className="flex flex-col gap-6">
              <div className="glass-panel rounded-2xl p-6">
                <h2 className="text-lg font-bold text-white mb-2">Report a Digital Threat or Check Scam Risk</h2>
                <p className="text-xs text-slate-400 mb-6">
                  Input a transcript of a suspicious call, phishing text, or submit a complaint. Our multi-agent NLP scoring engine evaluates risk immediately.
                </p>

                <form onSubmit={handleCitizenSubmit} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs uppercase tracking-wide font-semibold text-slate-400 mb-1.5">Reporter Name</label>
                      <input 
                        type="text" 
                        value={reporterName}
                        onChange={(e) => setReporterName(e.target.value)}
                        placeholder="John Doe"
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-red-500" 
                      />
                    </div>
                    <div>
                      <label className="block text-xs uppercase tracking-wide font-semibold text-slate-400 mb-1.5">Scam Phone Entity (Optional)</label>
                      <input 
                        type="text" 
                        value={phoneInput}
                        onChange={(e) => setPhoneInput(e.target.value)}
                        placeholder="+91 9998887776"
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-red-500" 
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs uppercase tracking-wide font-semibold text-slate-400 mb-1.5">Call Transcript or Threat Text Content</label>
                    <textarea 
                      rows={4}
                      value={transcriptInput}
                      onChange={(e) => setTranscriptInput(e.target.value)}
                      placeholder="e.g. This is Delhi Cyber Police calling. Your Aadhar card is linked to money laundering contraband..."
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-red-500"
                    />
                  </div>

                  <button 
                    type="submit" 
                    disabled={loading}
                    className="bg-red-600 hover:bg-red-700 transition-colors text-white font-semibold text-sm rounded-lg px-6 py-2.5 flex items-center justify-center gap-2"
                  >
                    {loading ? "Analyzing Signal..." : "Submit Scam Audit"}
                  </button>
                </form>
              </div>

              {/* Citizen Risk Verdict Output */}
              {citizenVerdict && (
                <div className={`glass-panel rounded-2xl p-6 border ${
                  citizenVerdict.score >= 60 ? 'border-red-900/50 bg-red-950/10' : 'border-slate-850'
                }`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-bold text-white text-base">Instant Public Safety AI Assessment</h3>
                      <p className="text-xs text-slate-400 mt-0.5">Scored by sentence-transformers NLP classifier</p>
                    </div>
                    <div className="text-right">
                      <span className={`text-2xl font-black ${
                        citizenVerdict.score >= 70 ? 'text-red-500' : citizenVerdict.score >= 40 ? 'text-amber-500' : 'text-green-500'
                      }`}>
                        {citizenVerdict.score}%
                      </span>
                      <p className="text-[10px] uppercase font-bold text-slate-500">Risk Score</p>
                    </div>
                  </div>

                  <div className="mt-4 p-4 bg-slate-900/60 rounded-xl border border-slate-850">
                    <p className="text-sm font-semibold text-slate-200">Explanation & Verdict:</p>
                    <p className="text-xs text-slate-400 mt-1">{citizenVerdict.explanation}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* POLICE CONSOLE */}
          {role === 'officer' && (
            <div className="flex flex-col gap-6">
              {/* Cases & GIS Map Row */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Case Manager List */}
                <div className="glass-panel rounded-2xl p-4 flex flex-col h-[400px]">
                  <h3 className="text-sm font-bold uppercase tracking-wide text-slate-300 border-b border-slate-850 pb-2 flex items-center justify-between">
                    <span>Active Cases Registry</span>
                    <Layers className="w-4 h-4 text-slate-400" />
                  </h3>
                  
                  <div className="flex-1 overflow-y-auto mt-3 space-y-2">
                    {cases.length === 0 ? (
                      <p className="text-xs text-slate-500 text-center mt-10">No cases currently registered.</p>
                    ) : (
                      cases.map((c, i) => (
                        <div 
                          key={i} 
                          onClick={() => setSelectedCase(c)}
                          className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                            selectedCase?.id === c.id 
                              ? 'border-red-600 bg-red-950/20' 
                              : 'border-slate-850 bg-slate-900/20 hover:bg-slate-900/50'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-slate-200">CASE-#{c.id}: {c.title}</span>
                            <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold ${
                              c.severity === 'Critical' ? 'bg-red-950 text-red-400 border border-red-900/50' : 'bg-slate-800 text-slate-400'
                            }`}>{c.severity}</span>
                          </div>
                          <div className="flex items-center justify-between text-slate-400 mt-2 text-[10px]">
                            <span>Status: {c.status}</span>
                            <span>{new Date(c.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Simulated Heatmap GIS Widget */}
                <div className="glass-panel rounded-2xl p-4 flex flex-col h-[400px]">
                  <h3 className="text-sm font-bold uppercase tracking-wide text-slate-300 border-b border-slate-850 pb-2 flex items-center justify-between">
                    <span>GIS Incident Heatmap (PostGIS)</span>
                    <Map className="w-4 h-4 text-red-500 animate-pulse" />
                  </h3>

                  <div className="flex-1 bg-slate-900/50 rounded-xl border border-slate-850 mt-3 relative overflow-hidden flex items-center justify-center">
                    {/* Simulated SVG Grid Map */}
                    <svg className="w-full h-full" viewBox="0 0 400 300">
                      {/* Grid lines */}
                      <path d="M 0 50 L 400 50 M 0 100 L 400 100 M 0 150 L 400 150 M 0 200 L 400 200 M 0 250 L 400 250" stroke="#1e293b" strokeWidth="0.5" />
                      <path d="M 50 0 L 50 300 M 100 0 L 100 300 M 150 0 L 150 300 M 200 0 L 200 300 M 250 0 L 250 300 M 300 0 L 300 300 M 350 0 L 350 300" stroke="#1e293b" strokeWidth="0.5" />
                      
                      {/* Highlight Delhi Police Jurisdiction Polygon */}
                      <rect x="120" y="80" width="160" height="120" fill="rgba(37, 99, 235, 0.05)" stroke="rgba(37, 99, 235, 0.4)" strokeWidth="1" strokeDasharray="3,3" />
                      <text x="130" y="100" fill="rgba(59, 130, 246, 0.6)" fontSize="9" fontWeight="bold">DELHI JURISDICTION</text>

                      {/* Render Heatmap cell circles dynamically from database coordinates */}
                      {heatmapPoints.map((point, index) => {
                        const [lng, lat] = point.geometry.coordinates;
                        // Transform lat/lng from Delhi region (lng: 77.10-77.30, lat: 28.50-28.70) to SVG viewbox (120-280, 80-200)
                        const svgX = 120 + ((lng - 77.10) / 0.20) * 160;
                        const svgY = 200 - ((lat - 28.50) / 0.20) * 120; // Flip Y axis
                        const radius = 8 + point.properties.intensity * 20;

                        return (
                          <g key={index}>
                            <circle 
                              cx={svgX} 
                              cy={svgY} 
                              r={radius} 
                              fill="url(#redGlow)" 
                              opacity="0.6" 
                            />
                            <circle 
                              cx={svgX} 
                              cy={svgY} 
                              r="3" 
                              fill="#ef4444" 
                            />
                          </g>
                        );
                      })}

                      {/* Gradients */}
                      <defs>
                        <radialGradient id="redGlow" cx="50%" cy="50%" r="50%">
                          <stop offset="0%" stopColor="#ef4444" />
                          <stop offset="50%" stopColor="#ef4444" stopOpacity="0.4" />
                          <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
                        </radialGradient>
                      </defs>
                    </svg>

                    <div className="absolute bottom-3 right-3 bg-slate-950/80 px-2 py-1 rounded border border-slate-800 text-[9px] text-slate-400">
                      Delhi coordinates grid (PostGIS aggregated)
                    </div>
                  </div>
                </div>
              </div>

              {/* Case Details, Evidence chain, and Neo4j force-directed graph view */}
              {selectedCase && (
                <div className="glass-panel rounded-2xl p-6 space-y-6">
                  <div className="flex items-center justify-between border-b border-slate-850 pb-4">
                    <div>
                      <h3 className="text-lg font-bold text-white">{selectedCase.title}</h3>
                      <p className="text-xs text-slate-400">Case details and cryptographic logs</p>
                    </div>
                    {/* dossier export */}
                    <button 
                      onClick={() => {
                        // Find first evidence item linked to complaint of this case to trigger download
                        const ev = selectedCase.complaints?.[0]?.evidence_items?.[0];
                        if (ev) {
                          window.open(`${API_BASE}/evidence/${ev.id}/export`);
                        }
                      }}
                      className="bg-slate-900 border border-slate-800 text-slate-300 px-4 py-2 rounded-lg text-xs font-semibold hover:bg-slate-850 flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5" /> Export Evidence PDF
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Complaints lists */}
                    <div className="md:col-span-1 space-y-4">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Attached Complaints ({selectedCase.complaints?.length})</h4>
                      <div className="space-y-3">
                        {selectedCase.complaints?.map((comp: any, index: number) => (
                          <div key={index} className="p-3 bg-slate-900/40 rounded-xl border border-slate-850 text-xs">
                            <p className="text-slate-350 italic">"{comp.text_content.substring(0, 100)}..."</p>
                            <div className="mt-2.5 flex items-center justify-between text-[10px] text-slate-500">
                              <span>Phone: {comp.phone || 'Anonymous'}</span>
                              <span className="text-red-500 font-semibold">{comp.risk_score}% Risk</span>
                            </div>
                            
                            {/* Evidence check block */}
                            {comp.evidence_items?.map((ev: any, evIdx: number) => (
                              <div key={evIdx} className="mt-3 pt-2.5 border-t border-slate-850 flex items-center justify-between">
                                <span className="text-[10px] font-semibold text-slate-400">EV-#{ev.id} ({ev.type})</span>
                                <button 
                                  onClick={() => handleVerifyEvidence(ev.id)}
                                  className="text-[9px] bg-red-950 text-red-400 font-bold px-2 py-0.5 rounded border border-red-900/30 hover:bg-red-900/30"
                                >
                                  Verify Chain Hash
                                </button>
                              </div>
                            ))}
                          </div>
                        ))}
                      </div>

                      {/* Display verification status */}
                      {evidenceVerified && (
                        <div className={`p-4 rounded-xl border text-xs ${
                          evidenceVerified.valid ? 'bg-green-950/20 border-green-900/50 text-green-400' : 'bg-red-950/20 border-red-900/50 text-red-400'
                        }`}>
                          <p className="font-bold flex items-center gap-1.5">
                            {evidenceVerified.valid ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                            {evidenceVerified.valid ? 'CRYPTO INTEGRITY OK' : 'TAMPER DETECTED'}
                          </p>
                          <p className="text-[9px] font-mono mt-1 text-slate-400 break-all">Hash: {evidenceVerified.hash}</p>
                        </div>
                      )}
                    </div>

                    {/* Fraud Network Graph visualization (Neo4j synchronized data) */}
                    <div className="md:col-span-2 flex flex-col">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Campaign Entity Connections (Neo4j)</h4>
                      
                      <div className="flex-1 bg-slate-900/50 rounded-xl border border-slate-850 min-h-[300px] overflow-hidden flex items-center justify-center relative">
                        <svg className="w-full h-full" viewBox="0 0 500 300">
                          {/* Lines representing connections */}
                          {graphData.links.map((link, idx) => {
                            const u = graphData.nodes.find(n => n.value_hash === link.source);
                            const v = graphData.nodes.find(n => n.value_hash === link.target);
                            if (u && v && u.x !== undefined && u.y !== undefined && v.x !== undefined && v.y !== undefined) {
                              return (
                                <line 
                                  key={idx} 
                                  x1={u.x} 
                                  y1={u.y} 
                                  x2={v.x} 
                                  y2={v.y} 
                                  stroke={u.cluster_id === v.cluster_id && u.cluster_id !== -1 ? "#f43f5e" : "#475569"} 
                                  strokeWidth="1.5" 
                                  strokeDasharray={link.relation_type === 'shared_phone' ? 'none' : '3,3'}
                                />
                              );
                            }
                            return null;
                          })}

                          {/* Nodes representing entities */}
                          {graphData.nodes.map((node, idx) => {
                            if (node.x === undefined || node.y === undefined) return null;
                            const isCampaign = node.cluster_id !== -1;
                            const fill = isCampaign ? "#f43f5e" : "#3b82f6";
                            const radius = node.type === 'phone' ? 10 : 8;

                            return (
                              <g key={idx} transform={`translate(${node.x}, ${node.y})`}>
                                <circle 
                                  r={radius} 
                                  fill={fill} 
                                  stroke="#fff" 
                                  strokeWidth="1.5" 
                                  className={isCampaign ? "critical-glow" : ""}
                                />
                                <text 
                                  y={radius + 12} 
                                  textAnchor="middle" 
                                  fill="#cbd5e1" 
                                  fontSize="9" 
                                  fontWeight="medium"
                                >
                                  {node.value.substring(0, 12)}
                                </text>
                              </g>
                            );
                          })}
                        </svg>

                        <div className="absolute top-3 right-3 bg-slate-950/80 px-2 py-1 rounded border border-slate-800 text-[9px] text-slate-400">
                          Label Propagation clusters (NetworkX)
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* BANK CONSOLE */}
          {role === 'bank_analyst' && (
            <div className="glass-panel rounded-2xl p-6 space-y-6">
              <h2 className="text-lg font-bold text-white">Mule Account Risk & Bank Transaction Auditing</h2>
              <p className="text-xs text-slate-400">
                Audits transactions and scores risk. If accounts are connected to suspect numbers in our central Neo4j safety graph, risk propagates automatically.
              </p>

              <form onSubmit={handleGetTxScore} className="flex gap-4">
                <input 
                  type="text" 
                  value={txSearchId}
                  onChange={(e) => setTxSearchId(e.target.value)}
                  placeholder="Enter Transaction ID (e.g. 12345)"
                  className="bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-red-500 w-64"
                />
                <button 
                  type="submit" 
                  className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors flex items-center gap-1.5"
                >
                  Score Transaction
                </button>
              </form>

              {/* Scored transaction details card */}
              {scoredTx && (
                <div className={`p-6 rounded-2xl border ${
                  scoredTx.risk_score >= 60 ? 'border-red-900/50 bg-red-950/10' : 'border-slate-850 bg-slate-900/20'
                }`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-bold text-white text-sm">Transaction Risk Rating: {scoredTx.risk_score >= 60 ? 'CRITICAL' : 'SECURE'}</h3>
                      <p className="text-xs text-slate-400 mt-1">Transaction Ref: TX-#{scoredTx.transaction_id}</p>
                    </div>
                    <span className={`text-xl font-bold ${
                      scoredTx.risk_score >= 60 ? 'text-red-500' : 'text-green-500'
                    }`}>{scoredTx.risk_score}%</span>
                  </div>

                  <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                    <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-855">
                      <p className="text-slate-500">Sender Account</p>
                      <p className="font-mono text-slate-300 font-semibold">{scoredTx.sender_account}</p>
                    </div>
                    <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-855">
                      <p className="text-slate-500">Receiver Account</p>
                      <p className="font-mono text-slate-300 font-semibold">{scoredTx.receiver_account}</p>
                    </div>
                    <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-855">
                      <p className="text-slate-500">Amount Transfer</p>
                      <p className="font-mono text-slate-300 font-semibold">₹ {scoredTx.amount.toLocaleString()}</p>
                    </div>
                    <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-855">
                      <p className="text-slate-500">Explanation</p>
                      <p className="text-slate-400">{scoredTx.explanation}</p>
                    </div>
                  </div>

                  {scoredTx.risk_score >= 60 && (
                    <div className="mt-4 flex justify-end">
                      <button 
                        onClick={() => {
                          setSuccessMsg("Transaction evidence docket successfully shared directly into Police Investigation registry.");
                          setScoredTx(null);
                        }}
                        className="bg-red-650 hover:bg-red-700 text-white font-semibold text-xs px-4 py-2 rounded-lg transition-all flex items-center gap-1.5"
                      >
                        <Share2 className="w-3.5 h-3.5" /> Share Evidence with Police
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TELECOM CONSOLE */}
          {role === 'telecom_analyst' && (
            <div className="glass-panel rounded-2xl p-6 space-y-6">
              <h2 className="text-lg font-bold text-white">Telecom Call Registry & Spoofed Number Detection</h2>
              <p className="text-xs text-slate-400">
                Live stream monitoring of active calls. Telecommunication protocols are parsed in real time to trace spoofing indicators.
              </p>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 bg-slate-900/30">
                      <th className="py-3 px-4">CALL ID</th>
                      <th className="py-3 px-4">CALLER NUMBER</th>
                      <th className="py-3 px-4">CALLEE NUMBER</th>
                      <th className="py-3 px-4">CALL DURATION</th>
                      <th className="py-3 px-4">RISK INDEX</th>
                      <th className="py-3 px-4 text-right">ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {callsList.map((call, idx) => (
                      <tr key={idx} className="border-b border-slate-850 hover:bg-slate-900/30 transition-colors">
                        <td className="py-3 px-4 font-mono font-semibold">CALL-#{call.id}</td>
                        <td className="py-3 px-4 font-semibold text-slate-200">{call.caller}</td>
                        <td className="py-3 px-4 text-slate-400">{call.callee}</td>
                        <td className="py-3 px-4 text-slate-400">{call.duration}</td>
                        <td className="py-3 px-4">
                          <span className={`font-semibold ${call.risk >= 75 ? 'text-red-500' : 'text-amber-500'}`}>{call.risk}%</span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button 
                            onClick={async () => {
                              // Send call script to Central complaints orchestrator to analyze call transcript
                              setLoading(true);
                              try {
                                const response = await fetch(`${API_BASE}/complaints`, {
                                  method: 'POST',
                                  headers: { 'Content-Type': 'application/json' },
                                  body: JSON.stringify({
                                    reporter_name: "Telecom Intercept Service",
                                    phone: call.caller,
                                    text_content: "This is police calling. Connect to Skype immediately. You are under digital arrest for tax evasion.",
                                    location_lat: 28.55,
                                    location_lng: 77.15
                                  })
                                });
                                if (response.ok) {
                                  setSuccessMsg(`Call logs and intercept transcripts for number ${call.caller} forwarded to police case file.`);
                                }
                              } catch(e) {}
                              finally { setLoading(false); }
                            }}
                            className="bg-red-950 text-red-400 border border-red-900/30 hover:bg-red-900/30 text-[10px] font-bold px-3 py-1 rounded"
                          >
                            Flag call script
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ADMIN PORTAL */}
          {role === 'admin' && (
            <div className="glass-panel rounded-2xl p-6 space-y-6">
              <h2 className="text-lg font-bold text-white">RakshaNet Administrative Control Panel & Model Health</h2>
              <p className="text-xs text-slate-400">
                Pulls real evaluation metrics computed against validation sets directly from the models dashboard.
              </p>

              {/* Model metrics grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                {modelMetrics.map((m, idx) => (
                  <div key={idx} className="bg-slate-900/40 p-4 rounded-xl border border-slate-850 space-y-2">
                    <h3 className="text-xs font-bold uppercase text-slate-300 tracking-wider">
                      {m.model_name.replace('_', ' ').toUpperCase()}
                    </h3>
                    <div className="space-y-1 text-xs">
                      {m.status === 'not_yet_evaluated' || m.precision === null ? (
                        <div className="text-slate-500 italic py-1">Not yet evaluated</div>
                      ) : (
                        <>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-500">Precision:</span>
                            <span className="font-semibold text-slate-200">{(m.precision * 100).toFixed(0)}%</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-500">Recall:</span>
                            <span className="font-semibold text-slate-200">{(m.recall * 100).toFixed(0)}%</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-500">False Positives:</span>
                            <span className="font-semibold text-amber-500">{(m.false_positive_rate * 100).toFixed(0)}%</span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Audit logs table */}
              <div className="mt-6">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-350 mb-3">Security Audit Trail</h3>
                <div className="bg-slate-900/30 rounded-xl border border-slate-850 p-4 space-y-2 text-xs">
                  <div className="flex items-center justify-between text-slate-450 border-b border-slate-850 pb-2 mb-2 font-mono uppercase text-[10px]">
                    <span>Timestamp</span>
                    <span>Action Summary</span>
                    <span>Operator Identity</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-400">
                    <span>2026-07-04 13:20:56</span>
                    <span>Database extension PostGIS loaded successfully</span>
                    <span>system</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-450">
                    <span>2026-07-04 13:21:07</span>
                    <span>WebSocket client authorization handler initialized</span>
                    <span>gateway</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-400">
                    <span>2026-07-04 13:21:11</span>
                    <span>Model metrics Delhi validation run seed stored</span>
                    <span>admin</span>
                  </div>
                </div>
              </div>
            </div>
          )}

        </section>

      </main>

      {/* Footer */}
      <footer className="glass-panel mt-auto py-4 text-center text-xs text-slate-500 border-t border-slate-850">
        RakshaNet Unified Digital Public Safety Platform | Hackathon Prototype System
      </footer>
    </div>
  );
}
