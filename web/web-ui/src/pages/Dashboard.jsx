import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, { 
  Background, 
  Controls,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
  Panel,
  MiniMap
} from 'reactflow';
import 'reactflow/dist/style.css';
import { 
  Network, 
  FileCode, 
  RefreshCw,
  ChevronRight,
  Activity,
  ArrowRight,
  Zap,
  Focus
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

// --- Utility ---
function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const API_BASE = 'http://localhost:8733';

// --- Spotlight Card Wrapper ---
const SpotlightCard = ({ children, className }) => {
  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    e.currentTarget.style.setProperty('--mouse-x', `${x}px`);
    e.currentTarget.style.setProperty('--mouse-y', `${y}px`);
  };

  return (
    <div 
      onMouseMove={handleMouseMove}
      className={`spotlight-card ${className || ''}`}
    >
      {children}
    </div>
  );
};

// --- Consumer View: High-Refinement Pulse ---
const ConsumerView = ({ stats, metrics, currentTask, nextAction }) => {
  const avgRisk = Object.values(metrics).reduce((acc, m) => acc + (m.risk_score || 0), 0) / (Object.keys(metrics).length || 1);
  const healthScore = Math.max(0, Math.min(100, (1 - avgRisk) * 100));
  
  return (
    <div className="flex-1 flex flex-col p-12 lg:p-20 bg-[#0A0A0A] overflow-y-auto custom-scrollbar relative z-10">
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-blue-500/5 blur-[150px] rounded-full pointer-events-none mix-blend-screen" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-6xl w-full mx-auto space-y-16 relative z-10"
      >
        <header className="flex flex-col md:flex-row justify-between items-start md:items-end gap-10">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-widest">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Stream Active
            </div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white">
              System verified.
            </h1>
            <p className="text-zinc-400 text-lg max-w-xl font-medium">
              HCR has mapped {stats.dependencies} causal links across {stats.files} modules. Entropy is within nominal parameters.
            </p>
          </div>

          <div className="flex gap-4">
             <SpotlightCard className="px-8 py-6 rounded-3xl bg-[#111111] border border-white/5 flex flex-col items-center justify-center">
                <div className="text-zinc-500 text-xs font-bold uppercase tracking-widest mb-1">Entropy</div>
                <div className="text-3xl font-bold text-white">0.04<span className="text-zinc-500 text-lg ml-1">η</span></div>
             </SpotlightCard>
             <div className="px-8 py-6 rounded-3xl bg-blue-600 text-white shadow-[0_0_40px_rgba(37,99,235,0.2)] flex flex-col items-center justify-center relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                <div className="text-blue-200 text-xs font-bold uppercase tracking-widest mb-1 relative z-10">Sync</div>
                <div className="text-3xl font-bold relative z-10">Stable</div>
             </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
           {/* Centerpiece: The Causal Pulse */}
           <SpotlightCard className="lg:col-span-8 relative h-[500px] bg-[#111111] border border-white/5 rounded-[3rem] overflow-hidden flex flex-col items-center justify-center group">
              <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff02_1px,transparent_1px),linear-gradient(to_bottom,#ffffff02_1px,transparent_1px)] bg-[size:40px_40px]" />
              
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] bg-blue-500/10 blur-[80px] rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-700" />
              
              <div className="relative z-10 flex flex-col items-center">
                 <div className="w-48 h-48 rounded-full bg-black border border-white/10 flex flex-col items-center justify-center shadow-[0_0_60px_rgba(0,0,0,0.8)] relative mb-8">
                    {[...Array(3)].map((_, i) => (
                      <motion.div
                        key={i}
                        animate={{ scale: [1, 1.5, 2.5], opacity: [0.3, 0.1, 0] }}
                        transition={{ duration: 4, repeat: Infinity, delay: i * 1.33 }}
                        className="absolute inset-0 border border-blue-500/40 rounded-full"
                      />
                    ))}
                    <div className="text-6xl font-bold text-white tracking-tight">{healthScore.toFixed(0)}</div>
                 </div>
                 <div className="text-zinc-500 text-xs font-bold uppercase tracking-widest">Integrity Index</div>
              </div>

              <div className="absolute bottom-8 left-8 right-8 flex justify-between items-end">
                 <div>
                    <div className="text-zinc-500 text-xs font-bold uppercase tracking-widest mb-1">Neural Runtime</div>
                    <div className="text-xl font-bold text-white tracking-tight">Phi_nc_v2.4</div>
                 </div>
                 <div className="flex gap-1.5 h-12 items-end">
                    {[...Array(24)].map((_, i) => (
                      <motion.div 
                        key={i}
                        animate={{ height: [4, Math.random() * 40 + 8, 4] }}
                        transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.05 }}
                        className="w-1.5 bg-blue-500/30 rounded-sm shadow-[0_0_10px_rgba(59,130,246,0.3)]"
                      />
                    ))}
                 </div>
              </div>
           </SpotlightCard>

           <div className="lg:col-span-4 space-y-6 flex flex-col">
              {/* Task Awareness Panel */}
              <SpotlightCard className="flex-1 p-8 bg-[#111111] border border-white/5 rounded-[2.5rem] flex flex-col justify-between">
                 <div className="flex items-center justify-between mb-8">
                    <h3 className="text-zinc-500 text-xs font-bold uppercase tracking-widest">Context</h3>
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse shadow-[0_0_10px_rgba(245,158,11,0.5)]" />
                 </div>
                 <div>
                    <p className="text-2xl font-bold text-white mb-4 leading-tight">{currentTask || "Scanning Pathways..."}</p>
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-zinc-300 text-xs font-medium">
                       Action: {nextAction || "Monitoring"}
                    </div>
                 </div>
              </SpotlightCard>

              {/* Vulnerability Panel */}
              <SpotlightCard className="p-8 bg-[#111111] border border-white/5 rounded-[2.5rem]">
                 <h3 className="text-zinc-500 text-xs font-bold uppercase tracking-widest mb-6">Entropy Peaks</h3>
                 <div className="space-y-3">
                    {Object.entries(metrics)
                      .sort((a, b) => b[1].risk_score - a[1].risk_score)
                      .slice(0, 3)
                      .map(([path, m]) => (
                        <div key={path} className="flex items-center justify-between p-4 rounded-2xl bg-zinc-900 border border-white/5 hover:border-white/10 transition-colors">
                           <div className="flex items-center gap-3">
                              <FileCode className="w-4 h-4 text-zinc-500" />
                              <span className="text-sm font-medium text-zinc-300 truncate max-w-[150px]">{path.split('/').pop()}</span>
                           </div>
                           <span className="text-amber-500 text-sm font-bold shadow-amber-500/20 drop-shadow-md">{(m.risk_score * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                 </div>
              </SpotlightCard>
           </div>
        </div>
      </motion.div>
    </div>
  );
};

// --- Custom Node ---
const FileNode = ({ data, selected }) => {
  const { metrics } = data;
  const riskScore = metrics?.risk_score || 0.2;
  const centrality = metrics?.centrality || 0.1;
  
  return (
    <div className={cn(
      "px-6 py-4 rounded-2xl border transition-all duration-300 flex flex-col justify-center relative overflow-hidden",
      selected 
        ? "bg-[#0A0A0A] border-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.3)] scale-105 z-50 text-white" 
        : "bg-[#111111] border-white/10 hover:border-white/20 hover:shadow-[0_0_20px_rgba(255,255,255,0.05)] text-zinc-300",
    )} style={{
      width: 200 + (centrality * 100),
    }}>
      {selected && <div className="absolute inset-0 bg-blue-500/5 mix-blend-screen pointer-events-none" />}
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-blue-500 !border-0 !-top-1" />
      
      <div className="flex items-center gap-3 mb-3 relative z-10">
        <FileCode className={cn("w-4 h-4", selected ? "text-blue-400" : "text-zinc-500")} />
        <span className="text-sm font-semibold truncate flex-1">{data.label}</span>
      </div>
      
      <div className="w-full space-y-1.5 relative z-10">
        <div className="flex justify-between items-center text-[10px] font-medium opacity-60">
           <span>Entropy</span>
           <span>{(riskScore * 100).toFixed(0)}%</span>
        </div>
        <div className="h-1 w-full bg-black/50 rounded-full overflow-hidden border border-white/5">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${riskScore * 100}%` }}
            className={cn("h-full", selected ? "bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,0.8)]" : "bg-blue-500/50")} 
          />
        </div>
      </div>
      
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-blue-500 !border-0 !-bottom-1" />
    </div>
  );
};

// --- Main Dashboard Component ---
export default function Dashboard() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [impactData, setImpactData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('loading');
  const [viewMode, setViewMode] = useState('consumer'); 
  const [metrics, setMetrics] = useState({});
  const [context, setContext] = useState({ current_task: '', next_action: '' });
  const [stats, setStats] = useState({ files: 0, dependencies: 0 });

  const nodeTypes = useMemo(() => ({ fileNode: FileNode }), []);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const graphRes = await fetch(`${API_BASE}/causal_graph`);
      const graphData = await graphRes.json();
      
      const contextRes = await fetch(`${API_BASE}/context`);
      const contextData = await contextRes.json();
      setContext(contextData);
      
      const metricsData = graphData.metrics || {};
      setMetrics(metricsData);
      
      if (!graphData.forward || Object.keys(graphData.forward).length === 0) {
        setStatus('empty');
        return;
      }
      
      const newNodes = [];
      const newEdges = [];
      const processed = new Set();
      
      let idx = 0;
      Object.entries(graphData.forward).forEach(([source, targets]) => {
        if (!processed.has(source)) {
          newNodes.push({
            id: source,
            type: 'fileNode',
            data: { 
              label: source.split('/').pop(), 
              path: source,
              metrics: metricsData[source] || { risk_score: 0.2, centrality: 0.1 }
            },
            position: { x: 200 + (idx % 4) * 350, y: 100 + Math.floor(idx / 4) * 250 },
          });
          processed.add(source);
          idx++;
        }

        targets.forEach((target) => {
          if (!processed.has(target)) {
            newNodes.push({
              id: target,
              type: 'fileNode',
              data: { 
                label: target.split('/').pop(), 
                path: target,
                metrics: metricsData[target] || { risk_score: 0.2, centrality: 0.1 }
              },
              position: { x: 200 + (idx % 4) * 350, y: 100 + Math.floor(idx / 4) * 250 },
            });
            processed.add(target);
            idx++;
          }
          newEdges.push({
            id: `${source}->${target}`,
            source,
            target,
            animated: true,
            style: { stroke: 'rgba(59, 130, 246, 0.4)', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(59, 130, 246, 0.4)' }
          });
        });
      });

      setNodes(newNodes);
      setEdges(newEdges);
      setStats({ files: processed.size, dependencies: newEdges.length });
      setStatus('online');
    } catch (err) {
      console.error(err);
      setStatus('offline');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const checkImpact = async (nodeId) => {
    try {
      setImpactData(null);
      const response = await fetch(`${API_BASE}/impact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: nodeId })
      });
      const data = await response.json();
      setImpactData(data.impacted_files || []);
    } catch (err) {
      console.error(err);
      setImpactData([]);
    }
  };

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
    checkImpact(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setImpactData(null);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="h-screen w-full flex flex-col bg-[#0A0A0A] text-zinc-300 font-sans overflow-hidden selection:bg-blue-500/30">
      {/* Editorial Header */}
      <header className="h-20 border-b border-white/5 flex items-center justify-between px-8 bg-black z-50 relative">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(59,130,246,0.05),transparent_50%)] pointer-events-none" />
        <div className="flex items-center gap-4 relative z-10">
          <div className="w-8 h-8 bg-white text-black rounded-lg flex items-center justify-center font-black text-lg italic shadow-[0_0_15px_rgba(255,255,255,0.2)]">Ω</div>
          <div>
            <h1 className="font-bold text-white tracking-tight leading-none mb-1">Causal Console</h1>
            <div className="flex items-center gap-2">
               <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.8)]" />
               <span className="text-zinc-500 text-[10px] font-medium tracking-wide">Connected</span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-4 relative z-10">
          <div className="flex bg-zinc-900 p-1 rounded-xl border border-white/5 shadow-inner">
            <button 
              onClick={() => setViewMode('consumer')}
              className={cn(
                "px-4 py-2 text-xs font-semibold rounded-lg transition-all",
                viewMode === 'consumer' ? "bg-zinc-800 text-white shadow-md border border-white/10" : "text-zinc-500 hover:text-zinc-300"
              )}
            >
              Overview
            </button>
            <button 
              onClick={() => setViewMode('expert')}
              className={cn(
                "px-4 py-2 text-xs font-semibold rounded-lg transition-all",
                viewMode === 'expert' ? "bg-zinc-800 text-white shadow-md border border-white/10" : "text-zinc-500 hover:text-zinc-300"
              )}
            >
              Graph View
            </button>
          </div>
          
          <button 
            onClick={fetchData}
            disabled={isLoading}
            className="w-10 h-10 flex items-center justify-center bg-zinc-900 text-zinc-400 hover:text-white rounded-xl transition-all border border-white/5 hover:border-white/10 shadow-sm"
          >
            <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
          </button>
        </div>
      </header>

      {/* Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {status === 'offline' || status === 'empty' ? (
          <main className="flex-1 flex flex-col items-center justify-center relative">
             <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.02)_0%,transparent_70%)]" />
             <div className="text-center space-y-8 relative z-10">
                <div className="w-20 h-20 bg-zinc-900 rounded-2xl flex items-center justify-center mx-auto border border-white/5 shadow-2xl relative">
                   <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-transparent via-white/5 to-transparent opacity-0 hover:opacity-100 transition-opacity" />
                   <Network className="w-8 h-8 text-zinc-600" />
                </div>
                <div>
                   <h3 className="text-3xl font-bold text-white mb-2">Awaiting Context</h3>
                   <p className="text-zinc-500">Initialize the HCR daemon to begin mapping.</p>
                </div>
                <button 
                  onClick={fetchData}
                  className="px-6 py-3 bg-white text-black font-semibold rounded-xl hover:bg-zinc-200 hover:scale-105 active:scale-95 transition-all shadow-xl"
                >
                  Retry Connection
                </button>
             </div>
          </main>
        ) : viewMode === 'consumer' ? (
          <ConsumerView 
            stats={stats} 
            metrics={metrics} 
            currentTask={context.current_task} 
            nextAction={context.next_action} 
          />
        ) : (
          <>
            <main className="flex-1 relative bg-[#0A0A0A]">
              <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff02_1px,transparent_1px),linear-gradient(to_bottom,#ffffff02_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />
              <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                fitView
                className="bg-transparent"
              >
                {/* No dotted background here since we use our custom grid */}
                <Controls className="!bg-[#111111] !border-white/5 !rounded-xl !p-1 !shadow-2xl" />
              </ReactFlow>
            </main>

            {/* Impact Sidebar */}
            <AnimatePresence>
              {selectedNode && (
                <motion.aside 
                  initial={{ x: '100%' }}
                  animate={{ x: 0 }}
                  exit={{ x: '100%' }}
                  transition={{ type: "tween", duration: 0.3 }}
                  className="w-[400px] bg-[#0A0A0A] border-l border-white/5 flex flex-col shadow-2xl z-50 absolute right-0 top-0 bottom-0"
                >
                  <div className="h-20 border-b border-white/5 flex items-center justify-between px-8 bg-[#0A0A0A] relative overflow-hidden">
                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(59,130,246,0.05),transparent_70%)]" />
                    <h2 className="text-sm font-bold text-white relative z-10">Impact Analysis</h2>
                    <button 
                      onClick={() => setSelectedNode(null)} 
                      className="w-8 h-8 bg-[#111111] border border-white/5 flex items-center justify-center text-zinc-400 hover:text-white rounded-lg transition-all relative z-10 hover:border-white/10"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                    <div className="mb-8">
                       <div className="flex items-center gap-4 mb-6">
                          <div className="w-12 h-12 rounded-xl bg-[#111111] border border-white/10 flex items-center justify-center shadow-[0_0_20px_rgba(255,255,255,0.02)] relative overflow-hidden">
                             <div className="absolute inset-0 bg-blue-500/10 mix-blend-screen" />
                             <FileCode className="w-6 h-6 text-blue-400 relative z-10" />
                          </div>
                          <div>
                             <div className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest mb-1">Target Module</div>
                             <div className="text-lg font-bold text-white tracking-tight">{selectedNode.data.label}</div>
                          </div>
                       </div>
                       <div className="p-3 bg-black border border-white/5 rounded-lg text-xs text-zinc-500 break-all font-mono shadow-inner">
                          {selectedNode.id}
                       </div>
                    </div>

                    <div>
                       <div className="flex items-center justify-between mb-4">
                          <span className="text-zinc-500 text-xs font-bold uppercase tracking-widest">Downstream Radius</span>
                          <span className="text-blue-400 text-xs font-bold">{impactData?.length || 0} Entities</span>
                       </div>
                       
                       {impactData && impactData.length > 0 ? (
                          <div className="space-y-2">
                            {impactData.map((file, i) => (
                              <motion.div 
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.05 }}
                                key={i} 
                                className="flex items-center gap-3 p-4 bg-[#111111] border border-white/5 rounded-xl hover:border-white/10 transition-colors shadow-sm"
                              >
                                <FileCode className="w-4 h-4 text-blue-500/50" />
                                <span className="text-sm text-zinc-300 truncate font-medium">{file.split('/').pop()}</span>
                              </motion.div>
                            ))}
                          </div>
                       ) : (
                          <div className="py-12 bg-[#111111]/50 border border-dashed border-white/10 rounded-2xl text-center flex flex-col items-center gap-4">
                             <Focus className="w-6 h-6 text-zinc-600" />
                             <p className="text-zinc-500 text-sm">No downstream impact detected.</p>
                          </div>
                       )}
                    </div>
                  </div>

                  <div className="p-8 border-t border-white/5 bg-[#0A0A0A] relative">
                     <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-blue-500/20 to-transparent" />
                     <button className="w-full py-4 bg-white text-black font-semibold rounded-xl hover:bg-zinc-200 transition-all flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_30px_rgba(255,255,255,0.2)]">
                        Execute Scan
                        <Zap className="w-4 h-4" />
                     </button>
                  </div>
                </motion.aside>
              )}
            </AnimatePresence>
          </>
        )}
      </div>
    </div>
  );
}
