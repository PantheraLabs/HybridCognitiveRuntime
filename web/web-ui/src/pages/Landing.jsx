import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowRight, 
  Terminal, 
  Activity,
  Cpu,
  BrainCircuit,
  MessageSquare,
  CheckCircle2,
  XCircle,
  Play
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import Navbar from '../components/Navbar';

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

// --- Animated Flow Line ---
const GlowingFlowLine = () => (
  <div className="absolute top-0 bottom-0 left-1/2 w-[1px] bg-white/5 -translate-x-1/2 overflow-hidden hidden md:block">
    <div className="w-full h-32 bg-gradient-to-b from-transparent via-blue-500 to-transparent animate-flow" />
  </div>
);

// --- Background Graph Animation ---
const AnimatedGraphBackground = () => {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-30 mix-blend-screen">
      <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="edge-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(59, 130, 246, 0.1)" />
            <stop offset="100%" stopColor="rgba(59, 130, 246, 0.4)" />
          </linearGradient>
        </defs>
        
        {/* Animated Nodes and Edges */}
        <g stroke="url(#edge-gradient)" strokeWidth="1" fill="none">
          <motion.path 
            d="M 100 200 Q 300 100 500 300 T 900 200" 
            animate={{ d: ["M 100 200 Q 300 100 500 300 T 900 200", "M 100 250 Q 250 50 500 350 T 900 150", "M 100 200 Q 300 100 500 300 T 900 200"] }}
            transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.path 
            d="M 200 400 Q 400 300 600 500 T 1000 400" 
            animate={{ d: ["M 200 400 Q 400 300 600 500 T 1000 400", "M 200 350 Q 450 400 600 450 T 1000 350", "M 200 400 Q 400 300 600 500 T 1000 400"] }}
            transition={{ duration: 12, repeat: Infinity, ease: "easeInOut", delay: 2 }}
          />
        </g>
        <g fill="rgba(255,255,255,0.05)">
          <circle cx="100" cy="200" r="4" />
          <circle cx="500" cy="300" r="6" />
          <circle cx="900" cy="200" r="4" />
          <circle cx="200" cy="400" r="4" />
          <circle cx="600" cy="500" r="5" />
          <circle cx="1000" cy="400" r="4" />
        </g>
      </svg>
    </div>
  );
};


const InteractiveOnboarding = () => {
  const [step, setStep] = useState(0);

  const runSimulation = () => {
    setStep(1);
    setTimeout(() => setStep(2), 1500);
    setTimeout(() => setStep(3), 3500);
  };

  return (
    <section className="py-32 px-6 relative">
      <div className="max-w-5xl mx-auto relative z-10">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">The Context Loss Problem</h2>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
            Standard AI assistants forget what you did 10 minutes ago. HCR builds a permanent, state-based memory of your entire development session.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Standard AI Panel */}
          <SpotlightCard className="bg-[#111111] border border-white/5 rounded-3xl p-6 shadow-xl">
            <div className="flex items-center gap-3 mb-8 pb-4 border-b border-white/5">
               <div className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-zinc-400" />
               </div>
               <div>
                  <div className="text-sm font-semibold text-zinc-200">Standard AI Assistant</div>
                  <div className="text-xs text-zinc-500 font-mono">Session: Stateless</div>
               </div>
            </div>

            <div className="space-y-4 font-mono text-sm">
               <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5 text-zinc-300">
                  <span className="text-zinc-500 mr-2">User:</span>
                  "Can you update the auth middleware we just wrote?"
               </div>
               
               {step >= 1 && (
                 <motion.div 
                   initial={{ opacity: 0, y: 10 }}
                   animate={{ opacity: 1, y: 0 }}
                   className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200"
                 >
                    <span className="text-red-500 mr-2">AI:</span>
                    {step === 1 ? "Thinking..." : "I'm sorry, I don't have the context of the auth middleware you just wrote. Could you paste the code?"}
                 </motion.div>
               )}
            </div>
            
            {step >= 2 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute top-6 right-6 text-red-500 flex items-center gap-1 text-xs font-bold uppercase tracking-wider">
                 <XCircle className="w-4 h-4" /> Context Lost
              </motion.div>
            )}
          </SpotlightCard>

          {/* HCR Panel */}
          <SpotlightCard className="bg-[#111111] border border-blue-500/20 rounded-3xl p-6 shadow-[0_0_50px_rgba(59,130,246,0.05)]">
            <div className="flex items-center gap-3 mb-8 pb-4 border-b border-white/5">
               <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                  <BrainCircuit className="w-4 h-4 text-blue-400" />
               </div>
               <div>
                  <div className="text-sm font-semibold text-zinc-200">HCR Operator</div>
                  <div className="text-xs text-blue-400 font-mono">Session: Stateful (v2.4)</div>
               </div>
            </div>

            <div className="space-y-4 font-mono text-sm">
               <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5 text-zinc-300">
                  <span className="text-zinc-500 mr-2">User:</span>
                  "Can you update the auth middleware we just wrote?"
               </div>

               {step >= 1 && (
                 <motion.div 
                   initial={{ opacity: 0, y: 10 }}
                   animate={{ opacity: 1, y: 0 }}
                   className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-200"
                 >
                    <span className="text-blue-500 mr-2">HCR:</span>
                    {step === 1 || step === 2 ? (
                      <span className="animate-pulse">Loading `auth/middleware.ts` from local memory...</span>
                    ) : (
                      "Context loaded. I see you just added JWT validation. Should I implement the refresh token logic now?"
                    )}
                 </motion.div>
               )}
            </div>

            {step >= 3 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute top-6 right-6 text-blue-500 flex items-center gap-1 text-xs font-bold uppercase tracking-wider">
                 <CheckCircle2 className="w-4 h-4" /> Memory Retained
              </motion.div>
            )}
          </SpotlightCard>
        </div>

        <div className="mt-12 flex justify-center">
           {step === 0 ? (
             <button 
               onClick={runSimulation}
               className="px-8 py-4 bg-white text-black font-semibold rounded-xl flex items-center gap-3 hover:scale-105 active:scale-95 transition-all shadow-xl"
             >
               <Play className="w-4 h-4" fill="currentColor" />
               Run Simulation
             </button>
           ) : (
             <button 
               onClick={() => setStep(0)}
               className="px-8 py-4 bg-white/5 text-white font-semibold rounded-xl flex items-center gap-3 hover:bg-white/10 transition-all"
             >
               Reset
             </button>
           )}
        </div>
      </div>
    </section>
  );
};

const FeatureGrid = () => {
  return (
    <section className="max-w-6xl mx-auto px-6 py-24 relative">
      <GlowingFlowLine />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        className="text-center mb-20 relative z-10 bg-[#0A0A0A] inline-block px-8 mx-auto w-full"
      >
        <h2 className="text-3xl font-bold tracking-tight mb-4">Architecture for Intelligence</h2>
        <p className="text-zinc-400">Minimal overhead. Maximum logical precision.</p>
      </motion.div>

      <div className="grid md:grid-cols-3 gap-8 relative z-10">
        <SpotlightCard className="p-8 rounded-3xl bg-[#111111] border border-white/5">
           <Activity className="w-8 h-8 text-blue-500 mb-6" />
           <h3 className="text-lg font-bold mb-3 text-white">Live State Tracking</h3>
           <p className="text-zinc-400 text-sm leading-relaxed">
             HCR runs locally, tracking every file edit, terminal command, and git commit to build a real-time causal graph of your session.
           </p>
        </SpotlightCard>
        <SpotlightCard className="p-8 rounded-3xl bg-[#111111] border border-white/5">
           <Cpu className="w-8 h-8 text-emerald-500 mb-6" />
           <h3 className="text-lg font-bold mb-3 text-white">Model Agnostic</h3>
           <p className="text-zinc-400 text-sm leading-relaxed">
             Intelligence is state, not tokens. HCR retains your context perfectly whether you are using Claude, GPT-4, or a local Ollama model.
           </p>
        </SpotlightCard>
        <SpotlightCard className="p-8 rounded-3xl bg-[#111111] border border-white/5">
           <Terminal className="w-8 h-8 text-purple-500 mb-6" />
           <h3 className="text-lg font-bold mb-3 text-white">IDE & MCP Native</h3>
           <p className="text-zinc-400 text-sm leading-relaxed">
             Plug HCR directly into Cursor, Windsurf, or Claude Desktop via the Model Context Protocol. Zero configuration required.
           </p>
        </SpotlightCard>
      </div>
    </section>
  );
};

export default function Landing() {
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0, 1], [0, 200]);

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-zinc-300 font-sans selection:bg-blue-500/30 overflow-x-hidden">
      <Navbar />
      
      {/* Neo-Minimalist Hero with GitHub-style dynamic motion */}
      <section className="relative pt-40 pb-20 px-6 flex flex-col items-center justify-center min-h-[85vh]">
        <AnimatedGraphBackground />
        
        <motion.div 
          style={{ y }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-4xl mx-auto relative z-10"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-widest mb-8">
             <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
             HCR Version 2.4 Live
          </div>

          <h1 className="text-6xl md:text-8xl font-bold tracking-tighter text-white mb-8 leading-[1.05]">
             Never start from <br/><span className="text-zinc-500">zero again.</span>
          </h1>

          <p className="text-xl md:text-2xl text-zinc-400 max-w-2xl mx-auto mb-12 font-medium">
            Stop re-explaining your codebase. HCR gives your AI assistant a permanent, state-based memory across sessions.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/app" className="px-8 py-4 bg-white text-black font-semibold rounded-xl hover:scale-105 active:scale-95 transition-all shadow-xl relative overflow-hidden group">
              <span className="relative z-10">Launch Console</span>
              <div className="absolute inset-0 bg-gradient-to-r from-blue-100 to-white opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>
            <a href="#onboarding" className="px-8 py-4 bg-zinc-900 text-white font-semibold rounded-xl border border-white/10 hover:bg-zinc-800 transition-all">
              See how it works
            </a>
          </div>
        </motion.div>
      </section>

      {/* Trusted By - Minimal */}
      <div className="py-12 border-y border-white/5 bg-[#111111]/50 relative z-10">
         <div className="max-w-5xl mx-auto px-6 flex justify-center gap-12 md:gap-24 opacity-40 grayscale">
            <div className="text-lg font-bold tracking-tight hover:grayscale-0 hover:opacity-100 transition-all cursor-default">NVIDIA</div>
            <div className="text-lg font-bold tracking-tight hover:grayscale-0 hover:opacity-100 transition-all cursor-default">Vercel</div>
            <div className="text-lg font-bold tracking-tight hover:grayscale-0 hover:opacity-100 transition-all cursor-default">Anthropic</div>
            <div className="text-lg font-bold tracking-tight hover:grayscale-0 hover:opacity-100 transition-all cursor-default">Linear</div>
         </div>
      </div>

      <div id="onboarding" className="relative">
        <GlowingFlowLine />
        <InteractiveOnboarding />
      </div>

      <FeatureGrid />

      {/* Clean Minimalist CTA */}
      <section className="py-32 px-6 relative">
         <GlowingFlowLine />
         <motion.div 
           initial={{ opacity: 0, scale: 0.95 }}
           whileInView={{ opacity: 1, scale: 1 }}
           viewport={{ once: true }}
           className="max-w-4xl mx-auto p-16 md:p-24 rounded-[3rem] bg-[#111111] border border-white/5 text-center relative z-10 overflow-hidden group"
         >
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(59,130,246,0.1)_0%,transparent_70%)] opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
            
            <h2 className="text-4xl md:text-6xl font-bold text-white tracking-tighter mb-6 relative z-10">Build with foresight.</h2>
            <p className="text-xl text-zinc-400 mb-12 max-w-xl mx-auto relative z-10">
              Join high-performance teams using HCR to eliminate the #1 pain point in AI development: context loss.
            </p>
            <Link to="/signup" className="inline-flex items-center gap-2 px-8 py-4 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-500 transition-all shadow-[0_0_40px_rgba(37,99,235,0.3)] hover:shadow-[0_0_60px_rgba(37,99,235,0.5)] relative z-10">
              Get Secure Access <ArrowRight className="w-4 h-4" />
            </Link>
         </motion.div>
      </section>

      <footer className="py-12 border-t border-white/5 text-center relative z-10 bg-[#0A0A0A]">
        <div className="flex items-center justify-center gap-2 mb-6">
           <div className="w-6 h-6 bg-white text-black rounded-md flex items-center justify-center font-black text-sm italic">Ω</div>
           <span className="font-bold tracking-tight text-white">HCR</span>
        </div>
        <p className="text-zinc-600 text-sm">© 2026 Panthera Labs. Intelligence is State.</p>
      </footer>
    </div>
  );
}

