import { useState } from 'react';
import { Landmark, Search, AlertTriangle, ShieldCheck, Share2 } from 'lucide-react';
import type { ScoredTransaction } from '../types';
import { api } from '../lib/api';

interface BankPortalProps {
  setSuccessMsg: (msg: string | null) => void;
  setErrorMsg: (msg: string | null) => void;
  loading: boolean;
  setLoading: (l: boolean) => void;
}

export function BankPortal({ setSuccessMsg, setErrorMsg, loading, setLoading }: BankPortalProps) {
  const [txSearchId, setTxSearchId] = useState('12345');
  const [scoredTx, setScoredTx] = useState<ScoredTransaction | null>(null);

  // Past audits to provide density and completeness
  const [pastAudits, setPastAudits] = useState<ScoredTransaction[]>([
    {
      transaction_id: '99201',
      sender_account: 'ACC-887729',
      receiver_account: 'MULE-009121',
      amount: 450000,
      risk_score: 92,
      explanation: 'Receiver account flag: linked directly to high-density scam nodes in Delhi NCR.'
    },
    {
      transaction_id: '99185',
      sender_account: 'ACC-441290',
      receiver_account: 'ACC-331002',
      amount: 15000,
      risk_score: 15,
      explanation: 'Secure transaction. Accounts cleared of fraud associations.'
    }
  ]);

  const handleGetTxScore = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!txSearchId.trim()) return;

    setLoading(true);
    setScoredTx(null);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const data = await api.getTransactionScore(txSearchId);
      setScoredTx(data);
      setSuccessMsg(`Transaction TX-#${txSearchId} scored successfully.`);
      
      // Prepend to past audits if it is not already there
      if (!pastAudits.some(a => a.transaction_id === data.transaction_id)) {
        setPastAudits(prev => [data, ...prev]);
      }
    } catch (err: any) {
      console.error(err);
      setErrorMsg("Failed to score transaction. Ensure the Transaction ID exists inside the database registry.");
    } finally {
      setLoading(false);
    }
  };

  const handleShareWithPolice = () => {
    if (!scoredTx) return;
    setSuccessMsg(`Transaction TX-#${scoredTx.transaction_id} evidence docket successfully shared directly into Police Investigation registry.`);
    setScoredTx(null);
  };

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-6">
      <div>
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Landmark className="w-5.5 h-5.5 text-blue-500" /> Mule Account & Financial Fraud Audits
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Input a transaction identifier to calculate risk indexes. The fusion scorer propagates threat weights if transacting accounts link back to known cybercrime campaigns.
        </p>
      </div>

      {/* Query Search Form */}
      <form onSubmit={handleGetTxScore} className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-500" />
          <input 
            type="text" 
            value={txSearchId}
            onChange={(e) => setTxSearchId(e.target.value)}
            placeholder="Enter Transaction ID (e.g. 12345)"
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
            required
          />
        </div>
        <button 
          type="submit" 
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 transition-colors text-white font-bold text-xs uppercase tracking-wider px-6 py-2.5 rounded-xl flex items-center justify-center gap-1.5 cursor-pointer shadow-lg shadow-blue-950/40"
        >
          {loading ? "Calculating..." : "Score Transaction"}
        </button>
      </form>

      {/* Active audit results layout */}
      {scoredTx && (
        <div className={`p-6 rounded-2xl border transition-all ${
          scoredTx.risk_score >= 60 ? 'border-red-500/30 bg-red-950/15' : 'border-slate-800 bg-slate-900/20'
        }`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-850 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-sm">
                  Risk Assessment: {scoredTx.risk_score >= 60 ? 'CRITICAL RISK DETECTED' : 'LOW RISK STATUS'}
                </h3>
                {scoredTx.risk_score >= 60 ? (
                  <span className="p-1 bg-red-950/40 text-red-500 rounded-full border border-red-900/50">
                    <AlertTriangle className="w-3.5 h-3.5" />
                  </span>
                ) : (
                  <span className="p-1 bg-emerald-950/40 text-emerald-500 rounded-full border border-emerald-900/50">
                    <ShieldCheck className="w-3.5 h-3.5" />
                  </span>
                )}
              </div>
              <p className="text-[10px] text-slate-500 mt-1 font-mono">TX REF: #{scoredTx.transaction_id}</p>
            </div>
            
            <div className="text-right">
              <span className={`text-2xl font-black tracking-tight ${
                scoredTx.risk_score >= 60 ? 'text-red-500' : 'text-emerald-400'
              }`}>
                {scoredTx.risk_score}%
              </span>
              <p className="text-[9px] uppercase font-bold text-slate-500">Risk Fusion Index</p>
            </div>
          </div>

          {/* Grid fields */}
          <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-900">
              <p className="text-slate-500 uppercase text-[9px] font-bold tracking-wider">Sender Account</p>
              <p className="font-mono text-slate-300 font-semibold mt-1">{scoredTx.sender_account}</p>
            </div>
            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-900 flex items-center justify-between">
              <div>
                <p className="text-slate-500 uppercase text-[9px] font-bold tracking-wider">Receiver Account</p>
                <p className="font-mono text-slate-300 font-semibold mt-1">{scoredTx.receiver_account}</p>
              </div>
              {scoredTx.risk_score >= 60 && (
                <span className="text-[8px] bg-red-950 text-red-400 font-bold px-2 py-0.5 rounded border border-red-900/40">FLAGGED MULE</span>
              )}
            </div>
            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-900">
              <p className="text-slate-500 uppercase text-[9px] font-bold tracking-wider">Amount Transferred</p>
              <p className="font-mono text-white font-black mt-1 text-sm">₹ {scoredTx.amount.toLocaleString()}</p>
            </div>
          </div>

          <div className="mt-4 p-4 bg-slate-950/40 rounded-xl border border-slate-900 text-xs">
            <p className="text-slate-400 leading-relaxed font-medium"><span className="text-slate-200 font-bold">Scoring Explanation:</span> {scoredTx.explanation}</p>
          </div>

          {scoredTx.risk_score >= 60 && (
            <div className="mt-4 flex justify-end">
              <button 
                onClick={handleShareWithPolice}
                className="bg-red-600 hover:bg-red-750 text-white font-bold text-[10px] uppercase tracking-wider px-4 py-2.5 rounded-xl transition-all flex items-center gap-1.5 cursor-pointer shadow-lg shadow-red-950/40"
              >
                <Share2 className="w-3.5 h-3.5" /> Forward Case Dossier to Police
              </button>
            </div>
          )}
        </div>
      )}

      {/* Historical Ledger Table */}
      <div className="pt-4 border-t border-slate-850">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-350 mb-3">Audits Ledger</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-850 text-slate-500 uppercase tracking-wider text-[9px]">
                <th className="py-2.5 px-3">Transaction ID</th>
                <th className="py-2.5 px-3">Sender</th>
                <th className="py-2.5 px-3">Receiver</th>
                <th className="py-2.5 px-3">Amount</th>
                <th className="py-2.5 px-3">Risk score</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900">
              {pastAudits.map((audit) => (
                <tr key={audit.transaction_id} className="hover:bg-slate-900/10 text-slate-350 transition-colors">
                  <td className="py-3 px-3 font-mono font-semibold">#{audit.transaction_id}</td>
                  <td className="py-3 px-3 font-mono text-[11px]">{audit.sender_account}</td>
                  <td className="py-3 px-3 font-mono text-[11px] flex items-center gap-1">
                    {audit.receiver_account}
                    {audit.risk_score >= 60 && <span className="w-1.5 h-1.5 rounded-full bg-red-500" />}
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-200">₹ {audit.amount.toLocaleString()}</td>
                  <td className="py-3 px-3">
                    <span className={`font-bold ${audit.risk_score >= 60 ? 'text-red-500' : 'text-emerald-400'}`}>
                      {audit.risk_score}%
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold ${
                      audit.risk_score >= 60 ? 'bg-red-950/40 text-red-400 border border-red-900/30' : 'bg-slate-900 text-slate-400 border border-slate-800'
                    }`}>
                      {audit.risk_score >= 60 ? 'Suspended' : 'Cleared'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
export default BankPortal;
