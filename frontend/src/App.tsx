import { useState, useEffect } from 'react';
import { Shield, Activity, X, User } from 'lucide-react';
import { api } from './lib/api';
import { useAlerts } from './hooks/useAlerts';
import type { Case, GraphNode, GraphLink, ModelMetric } from './types';

// Import Portal components
import { CitizenPortal } from './portals/CitizenPortal';
import { PolicePortal } from './portals/PolicePortal';
import { BankPortal } from './portals/BankPortal';
import { TelecomPortal } from './portals/TelecomPortal';
import { AdminPortal } from './portals/AdminPortal';

type Role = 'citizen' | 'officer' | 'bank_analyst' | 'telecom_analyst' | 'admin';

export default function App() {
  const [role, setRole] = useState<Role>('citizen');
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string>('');

  // General Notification States
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Portal Datasets
  const [cases, setCases] = useState<Case[]>([]);
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({ nodes: [], links: [] });
  const [heatmapPoints, setHeatmapPoints] = useState<any[]>([]);
  const [modelMetrics, setModelMetrics] = useState<ModelMetric[]>([]);

  // Real-time Alerts WebSockets manager hook
  const { alerts, wsConnected } = useAlerts(token);

  // Auto Login system when changing roles
  useEffect(() => {
    let user = 'citizen_john';
    let pass = 'citizen_pass';
    if (role === 'officer') { user = 'officer_delhi'; pass = 'officer_pass'; }
    else if (role === 'bank_analyst') { user = 'bank_analyst_sam'; pass = 'bank_pass'; }
    else if (role === 'telecom_analyst') { user = 'telecom_analyst_tina'; pass = 'telecom_pass'; }
    else if (role === 'admin') { user = 'admin'; pass = 'admin_pass'; }

    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);

    api.login(user, pass)
      .then(data => {
        setToken(data.access_token);
        setUsername(data.username);
        // Load datasets for that role
        fetchRoleData(role, data.access_token);
      })
      .catch(err => {
        console.error("Login failure:", err);
        setErrorMsg("Failed to authenticate session with the backend gateway.");
        setToken(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [role]);

  // Load specific database parameters for logged roles
  const fetchRoleData = async (activeRole: Role, tokenStr: string) => {
    try {
      if (activeRole === 'officer') {
        const [casesData, clusterData, geoData] = await Promise.all([
          api.getCases(tokenStr),
          api.getGraphCluster(tokenStr),
          api.getGeoHeatmap(tokenStr)
        ]);
        setCases(casesData);
        setGraphData(clusterData);
        setHeatmapPoints(geoData.features || []);
      } else if (activeRole === 'admin') {
        const metrics = await api.getModelMetrics(tokenStr);
        setModelMetrics(metrics);
      }
    } catch (e) {
      console.error("Error loading dashboard data:", e);
      setErrorMsg("Error syncing system database entries. Check gateway status.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col font-sans select-none antialiased">
      
      {/* Dynamic Toast Notifications */}
      <div className="fixed top-6 right-6 z-50 flex flex-col gap-3 max-w-sm w-full">
        {errorMsg && (
          <div className="bg-slate-900/90 border border-red-500/30 text-slate-200 p-4 rounded-2xl shadow-2xl backdrop-blur flex items-start gap-3 animate-slide-in">
            <div className="p-1 bg-red-950 text-red-500 rounded-lg border border-red-900/30 text-xs font-black">ALERT</div>
            <div className="flex-1 text-xs font-medium leading-relaxed">{errorMsg}</div>
            <button onClick={() => setErrorMsg(null)} className="text-slate-500 hover:text-slate-350 cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {successMsg && (
          <div className="bg-slate-900/90 border border-emerald-500/30 text-slate-200 p-4 rounded-2xl shadow-2xl backdrop-blur flex items-start gap-3 animate-slide-in">
            <div className="p-1 bg-emerald-950 text-emerald-500 rounded-lg border border-emerald-900/30 text-xs font-black">INFO</div>
            <div className="flex-1 text-xs font-medium leading-relaxed">{successMsg}</div>
            <button onClick={() => setSuccessMsg(null)} className="text-slate-500 hover:text-slate-350 cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Main Top Header */}
      <header className="glass-panel sticky top-0 z-40 px-6 py-3.5 flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-slate-900">
        <div className="flex items-center gap-3.5">
          <div className="p-2.5 bg-red-650 rounded-xl critical-glow flex items-center justify-center text-white">
            <Shield className="w-5.5 h-5.5" />
          </div>
          <div>
            <h1 className="text-base font-black tracking-wider text-white flex items-center gap-2">
              RAKSHANET
              <span className="text-[9px] bg-red-950 text-red-400 font-extrabold px-2 py-0.5 rounded-full border border-red-900/50 tracking-widest uppercase">
                Intel Gateway
              </span>
            </h1>
            <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mt-0.5">Digital Public Safety Infrastructure</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-4">
          {/* WebSocket Live Stream Connection Indicator */}
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-900 text-[10px]">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="uppercase font-bold tracking-wider text-slate-400">
              {wsConnected ? 'Stream Active' : 'Stream Offline'}
            </span>
          </div>

          {/* User badge */}
          {username && (
            <div className="flex items-center gap-2 bg-slate-900/40 border border-slate-900 px-3.5 py-1.5 rounded-xl text-[10px] text-slate-400 font-mono">
              <User className="w-3.5 h-3.5 text-slate-500" />
              <span>{username}</span>
            </div>
          )}

          {/* Access Switcher Selector */}
          <div className="flex items-center gap-2.5">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Access Scope:</span>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="bg-slate-950 border border-slate-850 text-slate-200 text-xs font-bold rounded-xl px-3 py-2 focus:ring-1 focus:ring-red-500 focus:outline-none cursor-pointer"
            >
              <option value="citizen">Citizen App</option>
              <option value="officer">Police Command</option>
              <option value="bank_analyst">Bank Audit</option>
              <option value="telecom_analyst">Telecom Intercept</option>
              <option value="admin">System Admin</option>
            </select>
          </div>
        </div>
      </header>

      {/* Main Container Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Left Col: Threat ticker feed */}
        <section className="lg:col-span-1 flex flex-col gap-4">
          <div className="glass-panel rounded-2xl p-4 flex flex-col h-[580px] overflow-hidden">
            <div className="flex items-center justify-between pb-3 border-b border-slate-900">
              <h2 className="text-xs font-black uppercase tracking-widest text-slate-350 flex items-center gap-1.5">
                <Activity className="w-4.5 h-4.5 text-red-500" /> Security Feeds
              </h2>
              <span className="text-[8px] bg-red-950 text-red-400 font-extrabold px-2 py-0.5 rounded border border-red-900/50 uppercase tracking-widest">
                Redis
              </span>
            </div>
            
            <div className="flex-1 overflow-y-auto mt-3 space-y-3 pr-1">
              {alerts.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-4">
                  <p className="text-[10px] font-semibold text-slate-650 tracking-wider">
                    {role === 'citizen'
                      ? "No updates yet. You'll see a live notification here as soon as one of your reports is scored."
                      : "Waiting for real-time Redis queue threat relays..."}
                  </p>
                </div>
              ) : (
                alerts.map((a, i) => {
                  const isCritical = a.severity === 'Critical';
                  return (
                    <div 
                      key={i} 
                      className={`p-3 rounded-xl border text-xs bg-slate-950/40 transition-all ${
                        isCritical ? 'border-red-900/40 hover:border-red-500/40' : 'border-slate-900 hover:border-slate-800'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className={`text-[8px] font-black uppercase tracking-widest ${
                          isCritical ? 'text-red-400' : 'text-amber-400'
                        }`}>
                          {a.severity} Threat
                        </span>
                        <span className="text-[8px] font-mono text-slate-600">Just Now</span>
                      </div>
                      <p className="font-bold text-slate-200 text-[11px] leading-tight">{a.title}</p>
                      <p className="text-slate-400 text-[10px] leading-relaxed mt-1.5">{a.description}</p>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </section>

        {/* Right Col: Active Portal workspace */}
        <section className="lg:col-span-3 flex flex-col gap-6">
          {loading && (
            <div className="w-full h-1 bg-slate-900 overflow-hidden rounded-full">
              <div className="h-full bg-red-500 animate-pulse w-1/3 rounded-full" />
            </div>
          )}

          {role === 'citizen' && (
            <CitizenPortal
              setSuccessMsg={setSuccessMsg}
              setErrorMsg={setErrorMsg}
              loading={loading}
              setLoading={setLoading}
            />
          )}

          {role === 'officer' && (
            <PolicePortal
              token={token || ''}
              cases={cases}
              setCases={setCases}
              graphData={graphData}
              setGraphData={setGraphData}
              heatmapPoints={heatmapPoints}
              setSuccessMsg={setSuccessMsg}
              setErrorMsg={setErrorMsg}
              loading={loading}
              setLoading={setLoading}
            />
          )}

          {role === 'bank_analyst' && (
            <BankPortal
              setSuccessMsg={setSuccessMsg}
              setErrorMsg={setErrorMsg}
              loading={loading}
              setLoading={setLoading}
            />
          )}

          {role === 'telecom_analyst' && (
            <TelecomPortal
              setSuccessMsg={setSuccessMsg}
              setErrorMsg={setErrorMsg}
              loading={loading}
              setLoading={setLoading}
            />
          )}

          {role === 'admin' && (
            <AdminPortal
              modelMetrics={modelMetrics}
            />
          )}
        </section>

      </main>

      {/* Footer */}
      <footer className="glass-panel py-3 text-center text-[10px] text-slate-500 font-mono tracking-wide uppercase border-t border-slate-900 mt-auto">
        RakshaNet Security Pipeline | Hackathon Deployment Module
      </footer>
    </div>
  );
}
