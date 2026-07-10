import { useState, useEffect } from 'react';
import { 
  Shield, Layers, Map, Download, AlertTriangle, 
  Search, Network, HelpCircle, Check
} from 'lucide-react';
import type { Case, GraphNode, GraphLink } from '../types';
import { api } from '../lib/api';

interface PolicePortalProps {
  token: string;
  cases: Case[];
  setCases: React.Dispatch<React.SetStateAction<Case[]>>;
  graphData: { nodes: GraphNode[]; links: GraphLink[] };
  setGraphData: React.Dispatch<React.SetStateAction<{ nodes: GraphNode[]; links: GraphLink[] }>>;
  heatmapPoints: any[];
  setSuccessMsg: (msg: string | null) => void;
  setErrorMsg: (msg: string | null) => void;
  loading: boolean;
  setLoading: (l: boolean) => void;
}

export function PolicePortal({
  token,
  cases,
  setCases: _setCases,
  graphData,
  setGraphData,
  heatmapPoints,
  setSuccessMsg,
  setErrorMsg,
  loading: _loading,
  setLoading
}: PolicePortalProps) {
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);
  const [evidenceVerified, setEvidenceVerified] = useState<{ [evId: number]: { valid: boolean; hash: string } }>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'details' | 'evidence' | 'network'>('details');

  // Keep track of dragged node for interactive force graph
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);

  // Filter cases based on search query
  const filteredCases = cases.filter(c => 
    c.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    c.id.toString().includes(searchQuery) ||
    c.severity.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Handle evidence verification
  const handleVerifyEvidence = async (evId: number) => {
    setLoading(true);
    try {
      const data = await api.verifyEvidence(evId, token);
      setEvidenceVerified(prev => ({
        ...prev,
        [evId]: {
          valid: data.verification.valid,
          hash: data.sha256_hash
        }
      }));
      if (data.verification.valid) {
        setSuccessMsg(`Cryptographic validation success: EV-#${evId} integrity holds.`);
      } else {
        setErrorMsg(`TAMPER ALARM: Verification failed on EV-#${evId}!`);
      }
    } catch (err: any) {
      console.error(err);
      setErrorMsg("Failed to run cryptographic audit.");
    } finally {
      setLoading(false);
    }
  };

  // Force-directed layout physics simulation hook
  useEffect(() => {
    if (graphData.nodes.length === 0) return;

    const width = 600;
    const height = 350;
    const padding = 20;

    // Initialize positions randomly if missing
    const nodes = graphData.nodes.map(n => ({
      ...n,
      x: n.x || width / 2 + (Math.random() - 0.5) * 250,
      y: n.y || height / 2 + (Math.random() - 0.5) * 200
    }));

    const links = [...graphData.links];

    // Physics parameters
    const repulsionStrength = 1800;
    const attractionStrength = 0.08;
    const centerGravity = 0.03;

    let animFrame: number;

    const tick = () => {
      // Repulsion between all node pairs
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

          if (dist < 180) {
            const force = repulsionStrength / distSq;
            fx += (dx / dist) * force;
            fy += (dy / dist) * force;
          }
        }
        u.x! += fx;
        u.y! += fy;
      }

      // Attraction along graph linkages
      for (const link of links) {
        const u = nodes.find(n => n.value_hash === link.source);
        const v = nodes.find(n => n.value_hash === link.target);

        if (u && v) {
          const dx = v.x! - u.x!;
          const dy = v.y! - u.y!;
          const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;
          const force = dist * attractionStrength * link.weight;
          const fX = (dx / dist) * force;
          const fY = (dy / dist) * force;

          u.x! += fX;
          u.y! += fY;
          v.x! -= fX;
          v.y! -= fY;
        }
      }

      // Gravity force pull to center of canvas and boundary locking
      for (const u of nodes) {
        const dX = width / 2 - u.x!;
        const dY = height / 2 - u.y!;
        u.x! += dX * centerGravity;
        u.y! += dY * centerGravity;

        // Constraint check
        u.x = Math.max(padding, Math.min(width - padding, u.x!));
        u.y = Math.max(padding, Math.min(height - padding, u.y!));
      }

      setGraphData({ nodes: [...nodes], links });
      animFrame = requestAnimationFrame(tick);
    };

    animFrame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animFrame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphData.links]);

  return (
    <div className="flex flex-col gap-6">
      {/* Overview stats panel */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel rounded-2xl p-4 flex items-center justify-between border-l-4 border-l-red-500">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Total Active Cases</span>
            <h3 className="text-xl font-bold text-white mt-1">{cases.length}</h3>
          </div>
          <Shield className="w-8 h-8 text-red-500/25" />
        </div>
        <div className="glass-panel rounded-2xl p-4 flex items-center justify-between border-l-4 border-l-amber-500">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Critical Escalations</span>
            <h3 className="text-xl font-bold text-white mt-1">
              {cases.filter(c => c.severity === 'Critical').length}
            </h3>
          </div>
          <AlertTriangle className="w-8 h-8 text-amber-500/25" />
        </div>
        <div className="glass-panel rounded-2xl p-4 flex items-center justify-between border-l-4 border-l-blue-500">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Network Campaigns</span>
            <h3 className="text-xl font-bold text-white mt-1">
              {new Set(graphData.nodes.map(n => n.cluster_id).filter(id => id !== -1)).size} Clusters
            </h3>
          </div>
          <Network className="w-8 h-8 text-blue-500/25" />
        </div>
        <div className="glass-panel rounded-2xl p-4 flex items-center justify-between border-l-4 border-l-emerald-500">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Geospatial Density</span>
            <h3 className="text-xl font-bold text-white mt-1">{heatmapPoints.length} Hotspots</h3>
          </div>
          <Map className="w-8 h-8 text-emerald-500/25" />
        </div>
      </div>

      {/* Main Grid: Cases Registry + GIS Map */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        
        {/* Left Col: Case List Registry */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-4 flex flex-col h-[480px]">
          <div className="pb-3 border-b border-slate-850 flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-red-500" /> Active Case Registry
            </h3>
            <span className="text-[9px] bg-red-950/40 text-red-400 font-bold px-2 py-0.5 rounded border border-red-900/50">GIS SYNC</span>
          </div>

          {/* Search bar inside list */}
          <div className="relative my-3">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-550" />
            <input
              type="text"
              placeholder="Search Case ID, Title or Severity..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-350 focus:outline-none focus:border-red-500"
            />
          </div>
          
          <div className="flex-grow overflow-y-auto space-y-2.5 pr-1">
            {filteredCases.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-4">
                <p className="text-xs text-slate-500">No cases matching search criteria.</p>
              </div>
            ) : (
              filteredCases.map((c) => (
                <div 
                  key={c.id} 
                  onClick={() => {
                    setSelectedCase(c);
                    setActiveTab('details');
                  }}
                  className={`p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                    selectedCase?.id === c.id 
                      ? 'border-red-500 bg-red-950/20 shadow-md shadow-red-950/30' 
                      : 'border-slate-850 bg-slate-900/10 hover:bg-slate-900/40'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-250 truncate max-w-[170px]">#{c.id}: {c.title}</span>
                    <span className={`px-2 py-0.5 rounded text-[8px] uppercase font-black border ${
                      c.severity === 'Critical' 
                        ? 'bg-red-950 text-red-400 border-red-900/50' 
                        : c.severity === 'High'
                        ? 'bg-amber-950 text-amber-400 border-amber-900/50'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}>{c.severity}</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-500 mt-3 text-[9px] font-medium">
                    <span>Status: <span className="text-slate-350 uppercase">{c.status}</span></span>
                    <span>{new Date(c.created_at).toLocaleString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Col: PostGIS GIS Heatmap Aggregation */}
        <div className="lg:col-span-3 glass-panel rounded-2xl p-4 flex flex-col h-[480px]">
          <div className="pb-3 border-b border-slate-850 flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <Map className="w-4 h-4 text-emerald-500" /> PostGIS Spatial Hotspots
            </h3>
            <span className="text-[10px] text-slate-500 font-mono">5.5km aggregated density grid</span>
          </div>

          <div className="flex-1 bg-slate-900/20 rounded-xl border border-slate-850 mt-3 relative overflow-hidden flex items-center justify-center">
            {/* Dark Tactical Map Grid */}
            <svg className="w-full h-full" viewBox="0 0 400 300">
              <defs>
                <radialGradient id="hotspotGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity="0.7"/>
                  <stop offset="45%" stopColor="#ef4444" stopOpacity="0.3"/>
                  <stop offset="100%" stopColor="#ef4444" stopOpacity="0"/>
                </radialGradient>
                <pattern id="grid-pattern" width="20" height="20" patternUnits="userSpaceOnUse">
                  <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#0f172a" strokeWidth="0.5"/>
                </pattern>
              </defs>

              <rect width="100%" height="100%" fill="url(#grid-pattern)" />
              
              {/* Delhi Boundary outline */}
              <rect x="80" y="50" width="240" height="190" fill="none" stroke="rgba(59, 130, 246, 0.25)" strokeWidth="1.5" strokeDasharray="4,4" />
              <text x="90" y="70" fill="rgba(59, 130, 246, 0.4)" fontSize="8" fontWeight="bold" letterSpacing="0.1em">NCR SECTOR ACTIVE JURISDICTION</text>

              {/* Aggregated cell grid plots */}
              {heatmapPoints.map((pt, idx) => {
                const [lng, lat] = pt.geometry.coordinates;
                // Transform NCR/Delhi bounds to fit SVG nicely
                const svgX = 80 + ((lng - 77.05) / 0.3) * 240;
                const svgY = 240 - ((lat - 28.45) / 0.3) * 190;
                const radius = 8 + (pt.properties.intensity || 1) * 18;

                return (
                  <g key={idx}>
                    <circle 
                      cx={svgX} 
                      cy={svgY} 
                      r={radius} 
                      fill="url(#hotspotGlow)" 
                    />
                    <circle 
                      cx={svgX} 
                      cy={svgY} 
                      r="2.5" 
                      fill="#f43f5e" 
                      className="animate-pulse"
                    />
                  </g>
                );
              })}
            </svg>

            <div className="absolute bottom-3 right-3 bg-slate-950/80 px-2 py-1 rounded border border-slate-800 text-[8px] font-mono text-slate-400 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> PostGIS aggregates compiled
            </div>
          </div>
        </div>

      </div>

      {/* Dynamic Inspector Panel (Case files, chain, Neo4j graphs) */}
      {selectedCase ? (
        <div className="glass-panel rounded-2xl p-5 space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-850 pb-4 gap-3">
            <div>
              <span className="text-[10px] text-red-500 font-bold uppercase tracking-wider">Case File Analysis</span>
              <h3 className="text-base font-bold text-white mt-0.5">#{selectedCase.id}: {selectedCase.title}</h3>
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const ev = selectedCase.complaints?.[0]?.evidence_items?.[0];
                  if (ev) {
                    window.open(api.getExportEvidencePdfUrl(ev.id));
                  } else {
                    setSuccessMsg("Export requested. Preparing canvas report streams...");
                  }
                }}
                className="bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-850 px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <Download className="w-4 h-4" /> Export Report (PDF)
              </button>
            </div>
          </div>

          {/* Sub tabs inside inspector */}
          <div className="flex border-b border-slate-850 text-xs">
            <button
              onClick={() => setActiveTab('details')}
              className={`pb-2.5 px-4 font-bold border-b-2 uppercase tracking-wider transition-all ${
                activeTab === 'details' ? 'border-red-500 text-red-400' : 'border-transparent text-slate-400'
              }`}
            >
              General Details
            </button>
            <button
              onClick={() => setActiveTab('evidence')}
              className={`pb-2.5 px-4 font-bold border-b-2 uppercase tracking-wider transition-all ${
                activeTab === 'evidence' ? 'border-red-500 text-red-400' : 'border-transparent text-slate-400'
              }`}
            >
              Cryptographic Custody ({selectedCase.complaints?.flatMap(c => c.evidence_items || []).length || 0})
            </button>
            <button
              onClick={() => setActiveTab('network')}
              className={`pb-2.5 px-4 font-bold border-b-2 uppercase tracking-wider transition-all ${
                activeTab === 'network' ? 'border-red-500 text-red-400' : 'border-transparent text-slate-400'
              }`}
            >
              Neo4j Ring Relationships
            </button>
          </div>

          <div className="pt-2">
            
            {/* SUBTAB 1: CASE COMPLAINTS AND INTEL */}
            {activeTab === 'details' && (
              <div className="space-y-4">
                <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Linked Citizen Intelligence feeds</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {selectedCase.complaints?.map((comp, idx) => (
                    <div key={idx} className="bg-slate-900/30 p-4 rounded-xl border border-slate-850 text-xs space-y-3">
                      <p className="text-slate-300 italic leading-relaxed">"{comp.text_content}"</p>
                      
                      <div className="flex items-center justify-between text-[9px] text-slate-500 border-t border-slate-850 pt-2.5 font-mono">
                        <span>Reporter: {comp.reporter_name || 'Anonymous'}</span>
                        <span>Phone: {comp.phone || 'N/A'}</span>
                        <span className="text-red-400 font-bold bg-red-950/20 px-2 py-0.5 rounded border border-red-900/30">{comp.risk_score}% Threat Index</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* SUBTAB 2: EVIDENCE VERIFICATION CHAIN */}
            {activeTab === 'evidence' && (
              <div className="space-y-4">
                <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Chain-of-Custody Cryptographic Records</h4>
                
                <div className="space-y-3">
                  {selectedCase.complaints?.flatMap(c => c.evidence_items || []).map((ev) => {
                    const verified = evidenceVerified[ev.id];
                    return (
                      <div key={ev.id} className="bg-slate-900/30 p-4 rounded-xl border border-slate-850 text-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-2">
                            <span className="bg-slate-800 text-slate-300 font-mono px-2 py-0.5 rounded font-semibold">EV-#{ev.id}</span>
                            <span className="text-slate-200 font-bold capitalize">{ev.type} Artifact</span>
                          </div>
                          <p className="text-slate-400 font-medium text-[11px]">{ev.description || "Evidence dossier binary details."}</p>
                        </div>

                        <div className="flex items-center gap-3">
                          {verified ? (
                            <div className={`px-3.5 py-2 rounded-xl border flex items-center gap-1.5 font-bold text-[10px] ${
                              verified.valid ? 'bg-green-950/30 border-green-900/50 text-green-400' : 'bg-red-950/30 border-red-900/50 text-red-400'
                            }`}>
                              {verified.valid ? (
                                <>
                                  <Check className="w-3.5 h-3.5" /> SECURE LEDGER OK
                                </>
                              ) : (
                                <>
                                  <AlertTriangle className="w-3.5 h-3.5" /> TAMPER WARNING
                                </>
                              )}
                            </div>
                          ) : null}

                          <button
                            onClick={() => handleVerifyEvidence(ev.id)}
                            className="bg-red-950 hover:bg-red-900/80 text-red-400 border border-red-900/30 font-bold text-[10px] uppercase tracking-wider px-3 py-2 rounded-xl transition-all cursor-pointer"
                          >
                            Audit Block Integrity
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* SUBTAB 3: Neo4j SPRING GRAPH FORCE SIMULATION */}
            {activeTab === 'network' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Spring physics graph linkage</h4>
                  <p className="text-[10px] text-slate-500">Entities with matching Campaign IDs are colored Red</p>
                </div>

                <div className="bg-slate-950 border border-slate-850 rounded-xl min-h-[350px] relative overflow-hidden flex items-center justify-center">
                  <svg className="w-full h-full" viewBox="0 0 600 350">
                    <defs>
                      <radialGradient id="ringGlow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.5" />
                        <stop offset="100%" stopColor="#f43f5e" stopOpacity="0" />
                      </radialGradient>
                    </defs>

                    {/* Links */}
                    {graphData.links.map((link, idx) => {
                      const u = graphData.nodes.find(n => n.value_hash === link.source);
                      const v = graphData.nodes.find(n => n.value_hash === link.target);
                      if (u && v && u.x !== undefined && u.y !== undefined && v.x !== undefined && v.y !== undefined) {
                        const isPrimary = u.cluster_id === v.cluster_id && u.cluster_id !== -1;
                        return (
                          <line 
                            key={idx} 
                            x1={u.x} 
                            y1={u.y} 
                            x2={v.x} 
                            y2={v.y} 
                            stroke={isPrimary ? "#f43f5e" : "#334155"} 
                            strokeWidth={isPrimary ? "1.8" : "1"} 
                            strokeDasharray={link.relation_type === 'shared_phone' ? 'none' : '4,4'}
                          />
                        );
                      }
                      return null;
                    })}

                    {/* Nodes */}
                    {graphData.nodes.map((node, idx) => {
                      if (node.x === undefined || node.y === undefined) return null;
                      const inCampaign = node.cluster_id !== -1;
                      const nodeRadius = node.type === 'phone' ? 11 : 9;
                      const isHovered = hoveredNode?.id === node.id;

                      return (
                        <g 
                          key={idx} 
                          transform={`translate(${node.x}, ${node.y})`}
                          onMouseEnter={() => setHoveredNode(node)}
                          onMouseLeave={() => setHoveredNode(null)}
                          className="cursor-pointer"
                        >
                          {inCampaign && (
                            <circle 
                              r={nodeRadius + 6} 
                              fill="url(#ringGlow)"
                              className="animate-ping"
                            />
                          )}
                          <circle 
                            r={nodeRadius} 
                            fill={inCampaign ? "#f43f5e" : "#3b82f6"} 
                            stroke="#0f172a" 
                            strokeWidth="1.5"
                          />
                          <text 
                            y={nodeRadius + 14} 
                            textAnchor="middle" 
                            fill={isHovered ? "#ffffff" : "#94a3b8"} 
                            fontSize="9" 
                            fontWeight={isHovered ? "bold" : "medium"}
                          >
                            {node.value.substring(0, 14)}
                          </text>
                        </g>
                      );
                    })}
                  </svg>

                  {/* Tooltip Overlay */}
                  {hoveredNode && (
                    <div className="absolute bottom-3 left-3 bg-slate-900/90 border border-slate-800 p-3 rounded-xl text-[10px] space-y-1 font-mono">
                      <p className="text-white font-bold uppercase">{hoveredNode.type} Entity</p>
                      <p className="text-slate-400">Value: {hoveredNode.value}</p>
                      <p className="text-slate-400">Risk index: {hoveredNode.risk_score}%</p>
                      <p className="text-slate-400">Campaign ID: {hoveredNode.cluster_id === -1 ? 'None' : hoveredNode.cluster_id}</p>
                    </div>
                  )}

                  <div className="absolute top-3 right-3 bg-slate-900/80 px-2 py-1 rounded border border-slate-800 text-[8px] font-mono text-slate-400">
                    Label Propagation algorithm active
                  </div>
                </div>
              </div>
            )}

          </div>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-8 text-center flex flex-col items-center justify-center min-h-[150px]">
          <HelpCircle className="w-8 h-8 text-slate-600 mb-2" />
          <p className="text-xs text-slate-500 font-semibold">Select a case file from the registry to run cryptographic chain checks and community analysis.</p>
        </div>
      )}
    </div>
  );
}
export default PolicePortal;
