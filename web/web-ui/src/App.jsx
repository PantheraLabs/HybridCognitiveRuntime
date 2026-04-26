import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, { 
  Background, 
  Controls,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
  Panel
} from 'reactflow';
import 'reactflow/dist/style.css';
import { 
  Network, 
  FileCode, 
  AlertCircle,
  RefreshCw,
  ChevronRight,
  Activity,
  Search,
  ExternalLink
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

// --- Utility ---
function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const API_BASE = 'http://localhost:8733';

// --- Empty State ---
const EmptyState = ({ onRetry, status }) => (
  <div className="flex flex-col items-center justify-center h-full text-center px-6">
    <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-6">
      {status === 'offline' ? (
        <AlertCircle className="w-8 h-8 text-slate-400" />
      ) : (
        <Network className="w-8 h-8 text-slate-400" />
      )}
    </div>
    <h3 className="text-lg font-semibold text-slate-900 mb-2">
      {status === 'offline' ? 'Engine Not Connected' : 'No Data Available'}
    </h3>
    <p className="text-slate-500 max-w-sm mb-6">
      {status === 'offline' 
        ? 'Start the HCR engine to visualize your project\'s causal dependencies.'
        : 'Edit some Python files to build the dependency graph.'}
    </p>
    {status === 'offline' && (
      <div className="bg-slate-900 text-slate-300 px-4 py-3 rounded-lg font-mono text-sm mb-4">
        python -m src.engine_server --project .
      </div>
    )}
    <button 
      onClick={onRetry}
      className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors"
    >
      <RefreshCw className="w-4 h-4" />
      Try Again
    </button>
  </div>
);

// --- Custom Node ---
const FileNode = ({ data, selected }) => {
  const impactSeverity = data.impactCount > 5 ? 'high' : data.impactCount > 2 ? 'medium' : 'low';
  
  return (
    <div className={cn(
      "px-4 py-2.5 rounded-lg border bg-white shadow-sm transition-all duration-200 min-w-[160px]",
      selected 
        ? "border-blue-500 ring-2 ring-blue-100 shadow-md" 
        : "border-slate-200 hover:border-slate-300 hover:shadow",
      impactSeverity === 'high' && !selected && "border-orange-200 bg-orange-50/30",
      impactSeverity === 'medium' && !selected && "border-amber-200 bg-amber-50/30"
    )}>
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-slate-400 !border-none" />
      
      <div className="flex items-center gap-2">
        <FileCode className={cn(
          "w-4 h-4",
          impactSeverity === 'high' ? "text-orange-500" : 
          impactSeverity === 'medium' ? "text-amber-500" : "text-slate-400"
        )} />
        <span className="text-sm font-medium text-slate-700 truncate">{data.label}</span>
      </div>
      
      {data.impactCount > 0 && (
        <div className="mt-1.5 flex items-center gap-1.5 text-xs text-slate-500">
          <span className={cn(
            "w-1.5 h-1.5 rounded-full",
            impactSeverity === 'high' ? "bg-orange-500" : 
            impactSeverity === 'medium' ? "bg-amber-500" : "bg-slate-300"
          )} />
          {data.impactCount} dependent{data.impactCount !== 1 ? 's' : ''}
        </div>
      )}
      
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-slate-400 !border-none" />
    </div>
  );
};

// --- Main App ---
export default function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [impactData, setImpactData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('loading'); // loading, online, offline, empty
  const [stats, setStats] = useState({ files: 0, dependencies: 0 });

  const nodeTypes = useMemo(() => ({ fileNode: FileNode }), []);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      const response = await fetch(`${API_BASE}/causal_graph`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (!response.ok) throw new Error('Failed to fetch');
      
      const data = await response.json();
      
      if (!data.forward || Object.keys(data.forward).length === 0) {
        setStatus('empty');
        setNodes([]);
        setEdges([]);
        setStats({ files: 0, dependencies: 0 });
        return;
      }
      
      const newNodes = [];
      const newEdges = [];
      const processed = new Set();
      
      // Calculate impact counts
      const impactCounts = {};
      Object.entries(data.forward).forEach(([source, targets]) => {
        targets.forEach(target => {
          impactCounts[target] = (impactCounts[target] || 0) + 1;
        });
      });

      // Build nodes and edges with simple grid layout
      let idx = 0;
      Object.entries(data.forward).forEach(([source, targets]) => {
        if (!processed.has(source)) {
          newNodes.push({
            id: source,
            type: 'fileNode',
            data: { 
              label: source.split('/').pop(), 
              path: source,
              impactCount: impactCounts[source] || 0
            },
            position: { 
              x: 100 + (idx % 5) * 220, 
              y: 100 + Math.floor(idx / 5) * 140 
            },
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
                impactCount: impactCounts[target] || 0
              },
              position: { 
                x: 100 + (idx % 5) * 220, 
                y: 100 + Math.floor(idx / 5) * 140 
              },
            });
            processed.add(target);
            idx++;
          }
          newEdges.push({
            id: `${source}->${target}`,
            source,
            target,
            animated: false,
            style: { stroke: '#cbd5e1', strokeWidth: 1.5 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' }
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

  // Calculate severity for selected node
  const selectedSeverity = useMemo(() => {
    if (!impactData) return null;
    if (impactData.length > 5) return { level: 'high', color: 'text-orange-600 bg-orange-50 border-orange-200' };
    if (impactData.length > 2) return { level: 'medium', color: 'text-amber-600 bg-amber-50 border-amber-200' };
    return { level: 'low', color: 'text-emerald-600 bg-emerald-50 border-emerald-200' };
  }, [impactData]);

  return (
    <div className="h-screen w-full flex flex-col bg-slate-50 font-sans overflow-hidden">
      {/* Header */}
      <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-4 lg:px-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-slate-900 rounded-lg flex items-center justify-center">
            <Network className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-slate-900 text-sm">HCR Causal Graph</h1>
            <p className="text-xs text-slate-500 hidden sm:block">
              {status === 'online' ? `${stats.files} files · ${stats.dependencies} dependencies` : status}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <div className={cn(
            "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
            status === 'online' ? "bg-emerald-100 text-emerald-700" :
            status === 'loading' ? "bg-amber-100 text-amber-700" :
            "bg-red-100 text-red-700"
          )}>
            <span className={cn(
              "w-1.5 h-1.5 rounded-full",
              status === 'online' ? "bg-emerald-500" :
              status === 'loading' ? "bg-amber-500 animate-pulse" :
              "bg-red-500"
            )} />
            {status === 'online' ? 'Live' : status === 'loading' ? 'Connecting' : 'Offline'}
          </div>
          
          <button 
            onClick={fetchData}
            disabled={isLoading}
            className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Graph Area */}
        <main className="flex-1 relative">
          {status === 'offline' || status === 'empty' ? (
            <EmptyState onRetry={fetchData} status={status} />
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              fitView
              minZoom={0.2}
              maxZoom={2}
              className="bg-slate-50"
            >
              <Background color="#cbd5e1" gap={20} size={1} />
              <Controls className="!bg-white !border-slate-200 !shadow-md" />
              
              {/* Floating Stats Panel */}
              <Panel position="bottom-left" className="m-4">
                <div className="bg-white border border-slate-200 rounded-lg shadow-sm px-3 py-2 text-xs text-slate-600">
                  <span className="font-medium">{stats.files}</span> files · 
                  <span className="font-medium"> {stats.dependencies}</span> dependencies
                </div>
              </Panel>
            </ReactFlow>
          )}
        </main>

        {/* Right Panel - Impact Analysis */}
        <AnimatePresence mode="wait">
          {selectedNode && (
            <motion.aside 
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 320, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              className="bg-white border-l border-slate-200 flex-shrink-0 overflow-hidden flex flex-col"
            >
              {/* Panel Header */}
              <div className="h-14 border-b border-slate-200 flex items-center justify-between px-4 flex-shrink-0">
                <h2 className="font-semibold text-slate-900 text-sm">Impact Analysis</h2>
                <button 
                  onClick={() => setSelectedNode(null)}
                  className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
                >
                  <ChevronRight className="w-4 h-4 rotate-90" />
                </button>
              </div>

              {/* Panel Content */}
              <div className="flex-1 overflow-y-auto p-4">
                {/* Selected File */}
                <div className="mb-6">
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2 block">
                    Selected File
                  </label>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <FileCode className="w-4 h-4 text-slate-400" />
                      <span className="font-medium text-slate-900 text-sm">{selectedNode.data.label}</span>
                    </div>
                    <p className="text-xs text-slate-500 font-mono truncate">{selectedNode.data.path}</p>
                  </div>
                </div>

                {/* Impact Summary */}
                <div className="mb-4">
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2 block">
                    Blast Radius
                  </label>
                  
                  {impactData === null ? (
                    <div className="flex items-center justify-center py-8">
                      <RefreshCw className="w-5 h-5 text-slate-400 animate-spin" />
                    </div>
                  ) : impactData.length === 0 ? (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-center">
                      <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-2">
                        <Activity className="w-4 h-4 text-emerald-600" />
                      </div>
                      <p className="text-sm text-emerald-800 font-medium">Safe to modify</p>
                      <p className="text-xs text-emerald-600 mt-1">No downstream dependencies</p>
                    </div>
                  ) : (
                    <div className={cn(
                      "rounded-lg border p-4 mb-4",
                      selectedSeverity?.color
                    )}>
                      <div className="flex items-center gap-2 mb-1">
                        <AlertCircle className="w-4 h-4" />
                        <span className="font-semibold text-sm">
                          {impactData.length} dependent file{impactData.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <p className="text-xs opacity-80">
                        Changes to this file will affect {impactData.length} other file{impactData.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  )}
                </div>

                {/* Affected Files List */}
                {impactData && impactData.length > 0 && (
                  <div>
                    <label className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2 block">
                      Affected Files
                    </label>
                    <div className="space-y-1">
                      {impactData.map((file, i) => (
                        <div 
                          key={i} 
                          className="flex items-center gap-2 p-2 hover:bg-slate-50 rounded-md group cursor-pointer transition-colors"
                        >
                          <FileCode className="w-3.5 h-3.5 text-slate-400" />
                          <span className="text-sm text-slate-700 truncate flex-1 font-mono text-xs">
                            {file}
                          </span>
                          <ExternalLink className="w-3.5 h-3.5 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Panel Footer */}
              <div className="border-t border-slate-200 p-4 flex-shrink-0">
                <button className="w-full py-2 bg-slate-900 text-white text-sm font-medium rounded-lg hover:bg-slate-800 transition-colors">
                  View in Editor
                </button>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
