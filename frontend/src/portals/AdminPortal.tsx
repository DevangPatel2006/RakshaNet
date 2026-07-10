import { Settings, Shield, Cpu, Activity, Server, AlertCircle } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, 
  Legend, ResponsiveContainer 
} from 'recharts';
import type { ModelMetric } from '../types';

interface AdminPortalProps {
  modelMetrics: ModelMetric[];
}

export function AdminPortal({ modelMetrics }: AdminPortalProps) {
  
  // Format model metrics data for charts
  const chartData = modelMetrics
    .filter(m => m.status !== 'not_yet_evaluated' && m.precision !== null)
    .map(m => ({
      name: m.model_name.replace(/_/g, ' ').toUpperCase(),
      Precision: Math.round((m.precision || 0) * 100),
      Recall: Math.round((m.recall || 0) * 100),
      'False Positive': Math.round((m.false_positive_rate || 0) * 100)
    }));

  const systemLogs = [
    { timestamp: '2026-07-10 08:44:12', summary: 'Orchestration worker thread verified with Neo4j clustering pools', operator: 'system', type: 'system' },
    { timestamp: '2026-07-10 07:12:05', summary: 'Live WebSocket alerts channel connected with client ID ws_99182', operator: 'gateway', type: 'event' },
    { timestamp: '2026-07-04 13:20:56', summary: 'Database extension PostGIS loaded successfully', operator: 'system', type: 'system' },
    { timestamp: '2026-07-04 13:21:07', summary: 'WebSocket client authorization handler initialized', operator: 'gateway', type: 'event' },
    { timestamp: '2026-07-04 13:21:11', summary: 'Model metrics Delhi validation run seed stored', operator: 'admin', type: 'config' }
  ];

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-6">
      
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-850 pb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Settings className="w-5.5 h-5.5 text-indigo-400" /> Admin Console & Model Health
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time assessment of AI architectures. Precision, recall, and false positive parameters are calculated against production verification datasets.
          </p>
        </div>

        {/* Operational Status */}
        <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-350">
          <Server className="w-4 h-4 text-emerald-500" />
          <span>Gateway: <span className="text-emerald-400 font-bold uppercase">Online</span></span>
        </div>
      </div>

      {/* Model Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {modelMetrics.map((m, idx) => {
          const isEvaluated = m.status !== 'not_yet_evaluated' && m.precision !== null;
          return (
            <div 
              key={idx} 
              className="bg-slate-950/80 p-4 rounded-xl border border-slate-850 space-y-3 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-black uppercase tracking-wider text-slate-200">
                    {m.model_name.replace(/_/g, ' ')}
                  </h3>
                  <Cpu className="w-4 h-4 text-slate-650" />
                </div>
                <div className="mt-2.5">
                  {isEvaluated ? (
                    <div className="space-y-1.5 text-xs">
                      <div className="flex items-center justify-between text-slate-450 font-medium">
                        <span>Precision:</span>
                        <span className="font-bold text-white">{(m.precision! * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-450 font-medium">
                        <span>Recall:</span>
                        <span className="font-bold text-white">{(m.recall! * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-450 font-medium">
                        <span>False Positives:</span>
                        <span className="font-bold text-amber-500">{(m.false_positive_rate! * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 text-[11px] text-slate-500 italic py-1">
                      <AlertCircle className="w-3.5 h-3.5" /> Unevaluated/Pending
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-3 pt-2.5 border-t border-slate-900 flex items-center justify-between text-[9px] font-mono">
                <span className="text-slate-600">STATE:</span>
                <span className={`font-bold ${isEvaluated ? 'text-emerald-500' : 'text-slate-500'}`}>
                  {isEvaluated ? 'ACTIVE RUN' : 'STANDBY'}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Model Diagnostic Charting */}
      {chartData.length > 0 && (
        <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-850 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-350 flex items-center gap-1.5">
            <Activity className="w-4.5 h-4.5 text-indigo-400" /> AI Performance Vectors
          </h3>
          <div className="h-56 text-xs mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={9} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={9} domain={[0, 100]} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '12px' }}
                  labelStyle={{ color: '#cbd5e1', fontWeight: 'bold' }}
                />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '10px' }} />
                <Bar dataKey="Precision" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Recall" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="False Positive" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Security Audit Trail Log */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-350 flex items-center gap-1.5">
          <Shield className="w-4.5 h-4.5 text-indigo-400" /> Security Audit Log Ledger
        </h3>
        
        <div className="bg-slate-950 border border-slate-850 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-slate-900/60 border-b border-slate-850 text-slate-500 uppercase tracking-widest text-[9px] font-mono">
                  <th className="py-2.5 px-4 text-left">Timestamp</th>
                  <th className="py-2.5 px-4 text-left">Action Summary</th>
                  <th className="py-2.5 px-4 text-right">Operator Identity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900 font-mono text-slate-350">
                {systemLogs.map((log, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/10 transition-colors">
                    <td className="py-3 px-4 text-slate-500 text-[10px] whitespace-nowrap">{log.timestamp}</td>
                    <td className="py-3 px-4 text-slate-300 text-[11px] font-sans">{log.summary}</td>
                    <td className="py-3 px-4 text-right text-[10px]">
                      <span className={`px-2 py-0.5 rounded font-semibold ${
                        log.operator === 'system' 
                          ? 'bg-slate-900 text-slate-400 border border-slate-800' 
                          : log.operator === 'admin'
                          ? 'bg-indigo-950/40 text-indigo-400 border border-indigo-900/30'
                          : 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/30'
                      }`}>
                        {log.operator}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

    </div>
  );
}
export default AdminPortal;
