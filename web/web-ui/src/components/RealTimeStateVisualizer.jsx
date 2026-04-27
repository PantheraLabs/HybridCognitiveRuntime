import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactFlow, { 
  Background, 
  Controls,
  useNodesState,
  useEdgesState,
  Panel,
  MiniMap,
  NodeToolbar,
  Handle,
  Position
} from 'reactflow';
import 'reactflow/dist/style.css';
import { 
  Activity, 
  Clock, 
  Layers, 
  Zap, 
  Shield, 
  Network,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  MoreHorizontal,
  Play,
  Pause,
  Settings
} from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

// Utility for tailwind class merging
function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// --- Real-Time Metrics Component ---
const RealTimeMetrics = ({ metrics }) => {
  const [displayMetrics, setDisplayMetrics] = useState(metrics);
  
  // Smooth metric transitions
  useEffect(() => {
    const interval = setInterval(() => {
      setDisplayMetrics(prev => ({
        token_efficiency: prev.token_efficiency + (metrics.token_efficiency - prev.token_efficiency) * 0.1,
        confidence: prev.confidence + (metrics.confidence - prev.confidence) * 0.1,
        uncertainty: prev.uncertainty + (metrics.uncertainty - prev.uncertainty) * 0.1,
        active_states: metrics.active_states,
        operators_executed: metrics.operators_executed,
      }));
    }, 100);
    
    return () => clearInterval(interval);
  }, [metrics]);

  const MetricCard = ({ label, value, unit, trend, color = "blue" }) => (
    <motion.div 
      layout
      className="glass-panel p-4 rounded-2xl flex flex-col items-start min-w-[140px]"
    >
      <div className="text-slate-400 text-xs mono-ui mb-1">{label}</div>
      <div className="flex items-baseline gap-2">
        <span className={cn("text-2xl font-bold serif-display", `text-${color}-400`)}>
          {typeof value === 'number' ? value.toFixed(2) : value}
        </span>
        {unit && <span className="text-slate-500 text-sm">{unit}</span>}
      </div>
      {trend && (
        <div className={cn("flex items-center gap-1 text-xs mt-1", 
          trend > 0 ? "text-green-400" : "text-red-400"
        )}>
          {trend > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {Math.abs(trend).toFixed(1)}%
        </div>
      )}
    </motion.div>
  );

  return (
    <div className="flex flex-wrap gap-4">
      <MetricCard 
        label="Token Efficiency" 
        value={displayMetrics.token_efficiency} 
        unit="x"
        trend={2.5}
        color="green"
      />
      <MetricCard 
        label="Confidence" 
        value={displayMetrics.confidence * 100} 
        unit="%"
        color="blue"
      />
      <MetricCard 
        label="Uncertainty" 
        value={displayMetrics.uncertainty * 100} 
        unit="%"
        color="amber"
      />
      <MetricCard 
        label="Active States" 
        value={displayMetrics.active_states} 
        color="purple"
      />
      <MetricCard 
        label="HCOs Executed" 
        value={displayMetrics.operators_executed} 
        color="cyan"
      />
    </div>
  );
};

// --- State Evolution Timeline ---
const StateTimeline = ({ history, onSelectVersion }) => {
  const [selectedVersion, setSelectedVersion] = useState(null);

  return (
    <div className="glass-panel rounded-2xl p-4 h-[400px] overflow-hidden flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold flex items-center gap-2">
          <Clock size={18} className="text-blue-400" />
          State Evolution
        </h3>
        <span className="text-slate-400 text-xs mono-ui">
          {history.length} versions
        </span>
      </div>
      
      <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2">
        <AnimatePresence>
          {history.slice().reverse().map((version, index) => (
            <motion.div
              key={version.hash}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ delay: index * 0.05 }}
              className={cn(
                "p-3 rounded-xl cursor-pointer transition-all group",
                selectedVersion === version.hash 
                  ? "bg-blue-500/20 border border-blue-500/50" 
                  : "bg-slate-800/50 hover:bg-slate-700/50"
              )}
              onClick={() => {
                setSelectedVersion(version.hash);
                onSelectVersion?.(version);
              }}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "w-8 h-8 rounded-lg flex items-center justify-center text-xs font-mono",
                    selectedVersion === version.hash
                      ? "bg-blue-500 text-white"
                      : "bg-slate-700 text-slate-400"
                  )}>
                    {version.hash.slice(0, 4)}
                  </div>
                  <div>
                    <p className="text-white text-sm font-medium">{version.message}</p>
                    <p className="text-slate-500 text-xs mono-ui">
                      {new Date(version.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="text-slate-500 text-xs mono-ui">
                  {(version.state_size_bytes / 1024).toFixed(1)} KB
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
};

// --- Causal Graph Visualization ---
const CausalGraphView = ({ nodes: initialNodes, edges: initialEdges, onNodeSelect }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes || []);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges || []);
  const [selectedNode, setSelectedNode] = useState(null);

  // Auto-refresh graph data
  useEffect(() => {
    const interval = setInterval(() => {
      // Simulate real-time updates
      setNodes(prev => prev.map(node => ({
        ...node,
        data: {
          ...node.data,
          activity: Math.random() > 0.7 ? 'high' : 'normal',
          lastUpdated: Date.now()
        }
      })));
    }, 2000);

    return () => clearInterval(interval);
  }, [setNodes]);

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
    onNodeSelect?.(node);
  }, [onNodeSelect]);

  const CustomNode = ({ data, selected }) => {
    const isActive = data.activity === 'high';
    
    return (
      <div className={cn(
        "relative p-3 rounded-xl min-w-[120px] transition-all duration-300",
        selected ? "ring-2 ring-blue-500" : "",
        isActive ? "animate-pulse" : ""
      )}>
        <Handle type="target" position={Position.Left} className="!bg-blue-500" />
        
        <div className={cn(
          "glass-panel p-3 rounded-lg",
          data.type === 'neural' ? "border-l-2 border-purple-500" :
          data.type === 'symbolic' ? "border-l-2 border-green-500" :
          data.type === 'causal' ? "border-l-2 border-amber-500" :
          "border-l-2 border-blue-500"
        )}>
          <div className="flex items-center gap-2 mb-1">
            {data.type === 'neural' && <Zap size={14} className="text-purple-400" />}
            {data.type === 'symbolic' && <Layers size={14} className="text-green-400" />}
            {data.type === 'causal' && <Network size={14} className="text-amber-400" />}
            <span className="text-white text-sm font-medium">{data.label}</span>
          </div>
          <div className="text-slate-400 text-xs mono-ui">
            conf: {(data.confidence * 100).toFixed(0)}%
          </div>
          {isActive && (
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-ping" />
          )}
        </div>
        
        <Handle type="source" position={Position.Right} className="!bg-blue-500" />
      </div>
    );
  };

  const nodeTypes = {
    custom: CustomNode,
  };

  return (
    <div className="glass-panel rounded-2xl h-[600px] overflow-hidden relative">
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
        <div className="glass-panel px-3 py-1.5 rounded-lg flex items-center gap-2">
          <Network size={16} className="text-blue-400" />
          <span className="text-white text-sm font-medium">
            Causal Graph :: {nodes.length} nodes, {edges.length} edges
          </span>
        </div>
        <div className="flex gap-2">
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <div className="w-2 h-2 rounded-full bg-purple-500" />
            Neural
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            Symbolic
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <div className="w-2 h-2 rounded-full bg-amber-500" />
            Causal
          </div>
        </div>
      </div>
      
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
      >
        <Background color="#334155" gap={16} size={1} />
        <Controls className="!bg-slate-800 !text-white !border-slate-700" />
        <MiniMap 
          className="!bg-slate-800 !border-slate-700"
          nodeColor={(node) => {
            if (node.data.type === 'neural') return '#a855f7';
            if (node.data.type === 'symbolic') return '#22c55e';
            if (node.data.type === 'causal') return '#f59e0b';
            return '#3b82f6';
          }}
        />
      </ReactFlow>
      
      {selectedNode && (
        <NodeDetailsPanel 
          node={selectedNode} 
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
};

// --- Node Details Panel ---
const NodeDetailsPanel = ({ node, onClose }) => {
  return (
    <motion.div
      initial={{ opacity: 0, x: 300 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 300 }}
      className="absolute right-4 top-4 bottom-4 w-80 glass-panel rounded-2xl p-4 z-20 overflow-y-auto"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold">Node Details</h3>
        <button 
          onClick={onClose}
          className="p-1 hover:bg-slate-700 rounded-lg transition-colors"
        >
          <XCircle size={20} className="text-slate-400" />
        </button>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="text-slate-400 text-xs mono-ui">ID</label>
          <p className="text-white text-sm font-mono">{node.id}</p>
        </div>
        <div>
          <label className="text-slate-400 text-xs mono-ui">Label</label>
          <p className="text-white">{node.data.label}</p>
        </div>
        <div>
          <label className="text-slate-400 text-xs mono-ui">Type</label>
          <p className="text-white capitalize">{node.data.type} Operator</p>
        </div>
        <div>
          <label className="text-slate-400 text-xs mono-ui">Confidence</label>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-slate-700 h-2 rounded-full overflow-hidden">
              <div 
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${node.data.confidence * 100}%` }}
              />
            </div>
            <span className="text-white text-sm">{(node.data.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
        {node.data.metadata && (
          <div>
            <label className="text-slate-400 text-xs mono-ui">Metadata</label>
            <pre className="text-xs text-slate-300 bg-slate-800/50 p-2 rounded-lg overflow-x-auto">
              {JSON.stringify(node.data.metadata, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </motion.div>
  );
};

// --- System Health Monitor ---
const SystemHealthMonitor = ({ health }) => {
  const getStatusColor = (status) => {
    if (status === 'healthy') return 'text-green-400';
    if (status === 'warning') return 'text-amber-400';
    if (status === 'critical') return 'text-red-400';
    return 'text-slate-400';
  };

  const getStatusIcon = (status) => {
    if (status === 'healthy') return <CheckCircle size={16} className="text-green-400" />;
    if (status === 'warning') return <AlertCircle size={16} className="text-amber-400" />;
    if (status === 'critical') return <XCircle size={16} className="text-red-400" />;
    return <Activity size={16} className="text-slate-400" />;
  };

  return (
    <div className="glass-panel rounded-2xl p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold flex items-center gap-2">
          <Activity size={18} className="text-green-400" />
          System Health
        </h3>
        <span className={cn("text-xs mono-ui px-2 py-1 rounded-full bg-slate-800", getStatusColor(health.overall))}>
          {health.overall.toUpperCase()}
        </span>
      </div>
      
      <div className="space-y-3">
        {Object.entries(health.components || {}).map(([name, component]) => (
          <div key={name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {getStatusIcon(component.status)}
              <span className="text-slate-300 text-sm capitalize">{name}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 w-24 bg-slate-700 h-1.5 rounded-full overflow-hidden">
                <div 
                  className={cn(
                    "h-full rounded-full transition-all",
                    component.status === 'healthy' ? "bg-green-500" :
                    component.status === 'warning' ? "bg-amber-500" : "bg-red-500"
                  )}
                  style={{ width: `${component.load || 0}%` }}
                />
              </div>
              <span className="text-slate-400 text-xs mono-ui w-12 text-right">
                {component.load?.toFixed(0)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// --- Main Real-Time State Visualizer ---
const RealTimeStateVisualizer = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLive, setIsLive] = useState(true);
  const [metrics, setMetrics] = useState({
    token_efficiency: 85.4,
    confidence: 0.87,
    uncertainty: 0.13,
    active_states: 12,
    operators_executed: 142,
  });
  const [health, setHealth] = useState({
    overall: 'healthy',
    components: {
      engine: { status: 'healthy', load: 45 },
      storage: { status: 'healthy', load: 32 },
      network: { status: 'healthy', load: 12 },
      memory: { status: 'warning', load: 78 },
    }
  });
  const [versionHistory, setVersionHistory] = useState([
    { hash: 'a1b2c3d4', message: 'Auto-save: State update', timestamp: new Date().toISOString(), state_size_bytes: 45234 },
    { hash: 'e5f6g7h8', message: 'User action: Intent inference', timestamp: new Date(Date.now() - 60000).toISOString(), state_size_bytes: 45189 },
    { hash: 'i9j0k1l2', message: 'Auto-save: Git state changed', timestamp: new Date(Date.now() - 120000).toISOString(), state_size_bytes: 45012 },
  ]);

  // WebSocket simulation for real-time updates
  useEffect(() => {
    if (!isLive) return;

    const interval = setInterval(() => {
      // Simulate real-time metric updates
      setMetrics(prev => ({
        ...prev,
        confidence: Math.max(0, Math.min(1, prev.confidence + (Math.random() - 0.5) * 0.02)),
        operators_executed: prev.operators_executed + Math.floor(Math.random() * 3),
      }));

      // Simulate health updates
      setHealth(prev => ({
        ...prev,
        components: {
          ...prev.components,
          memory: {
            ...prev.components.memory,
            load: Math.min(100, prev.components.memory.load + (Math.random() - 0.5) * 10)
          }
        }
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, [isLive]);

  // Simulate version history updates
  useEffect(() => {
    if (!isLive) return;

    const interval = setInterval(() => {
      if (Math.random() > 0.7) {
        setVersionHistory(prev => [
          {
            hash: Math.random().toString(36).substring(2, 10),
            message: 'Auto-save: Real-time update',
            timestamp: new Date().toISOString(),
            state_size_bytes: 45000 + Math.floor(Math.random() * 5000)
          },
          ...prev.slice(0, 19)
        ]);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [isLive]);

  // Sample graph data
  const [graphNodes, setGraphNodes] = useState([
    { id: '1', type: 'custom', position: { x: 100, y: 100 }, data: { label: 'Input State', type: 'neural', confidence: 0.92, metadata: { latency: '12ms' } } },
    { id: '2', type: 'custom', position: { x: 300, y: 50 }, data: { label: 'Neural Φ_n', type: 'neural', confidence: 0.88, metadata: { iterations: 3 } } },
    { id: '3', type: 'custom', position: { x: 300, y: 150 }, data: { label: 'Symbolic Φ_s', type: 'symbolic', confidence: 0.95, metadata: { rules_applied: 12 } } },
    { id: '4', type: 'custom', position: { x: 500, y: 100 }, data: { label: 'Policy Π', type: 'causal', confidence: 0.87, metadata: { selector: 'adaptive' } } },
    { id: '5', type: 'custom', position: { x: 700, y: 100 }, data: { label: 'ΔS Transition', type: 'causal', confidence: 0.91, metadata: { delta_type: 'merge' } } },
    { id: '6', type: 'custom', position: { x: 900, y: 100 }, data: { label: 'Output State', type: 'neural', confidence: 0.93, metadata: { convergence: true } } },
  ]);

  const [graphEdges, setGraphEdges] = useState([
    { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#a855f7' } },
    { id: 'e1-3', source: '1', target: '3', animated: true, style: { stroke: '#22c55e' } },
    { id: 'e2-4', source: '2', target: '4', animated: true, style: { stroke: '#f59e0b' } },
    { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: '#f59e0b' } },
    { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
    { id: 'e5-6', source: '5', target: '6', animated: true, style: { stroke: '#3b82f6' } },
  ]);

  const handleRefresh = () => {
    // Trigger manual refresh
    setIsConnected(false);
    setTimeout(() => setIsConnected(true), 500);
  };

  return (
    <div className="min-h-screen bg-[#080808] text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-black serif-display italic">
            Real-Time State <span className="text-blue-500">Visualizer</span>
          </h1>
          <p className="text-slate-400 mt-1">
            Live cognitive state monitoring and causal graph visualization
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Connection Status */}
          <div className="flex items-center gap-2 glass-panel px-3 py-2 rounded-lg">
            <div className={cn(
              "w-2 h-2 rounded-full",
              isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
            )} />
            <span className="text-sm text-slate-300">
              {isConnected ? "Live Stream" : "Disconnected"}
            </span>
          </div>
          
          {/* Live Toggle */}
          <button
            onClick={() => setIsLive(!isLive)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg transition-all",
              isLive 
                ? "bg-red-500/20 text-red-400 hover:bg-red-500/30" 
                : "bg-green-500/20 text-green-400 hover:bg-green-500/30"
            )}
          >
            {isLive ? <Pause size={16} /> : <Play size={16} />}
            {isLive ? "Pause" : "Resume"}
          </button>
          
          {/* Refresh */}
          <button
            onClick={handleRefresh}
            className="p-2 glass-panel rounded-lg hover:bg-slate-700/50 transition-colors"
          >
            <RefreshCw size={18} className={cn("text-slate-400", isConnected && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column: Metrics & Health */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          {/* Real-Time Metrics */}
          <RealTimeMetrics metrics={metrics} />
          
          {/* System Health */}
          <SystemHealthMonitor health={health} />
          
          {/* State Timeline */}
          <StateTimeline 
            history={versionHistory}
            onSelectVersion={(version) => console.log('Selected version:', version)}
          />
        </div>

        {/* Right Column: Causal Graph */}
        <div className="col-span-12 lg:col-span-8">
          <CausalGraphView 
            nodes={graphNodes}
            edges={graphEdges}
            onNodeSelect={(node) => console.log('Selected node:', node)}
          />
        </div>
      </div>
    </div>
  );
};

export default RealTimeStateVisualizer;
