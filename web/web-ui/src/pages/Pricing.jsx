import React from 'react';
import { Link } from 'react-router-dom';
import { Shield, Cpu, ArrowRight, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
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

export default function Pricing() {
  const plans = [
    {
      name: "Researcher",
      price: "$0",
      description: "For individual builders mapping local complexity.",
      features: [
        "Static Causal Discovery",
        "Local Engine Runtime",
        "Community Logic Maps",
        "Standard Φ_nc Inference"
      ],
      cta: "Initialize",
      featured: false
    },
    {
      name: "Neural Pro",
      price: "$39",
      description: "Advanced causal intelligence for high-velocity teams.",
      features: [
        "Cloud-Synced Causal Graph",
        "Latent Link Discovery",
        "Predictive Blast Radius",
        "Priority Neural Clusters",
        "Team Identity Sync",
        "24/7 Cognitive Support"
      ],
      cta: "Launch Pro",
      featured: true
    },
    {
      name: "Infinite",
      price: "Contact",
      description: "Custom cognitive architecture for global enterprises.",
      features: [
        "On-Premise Deployment",
        "Private Neural Clusters",
        "Custom Compliance Operators",
        "Unlimited Logic Modules",
        "White-Glove Integration",
        "SLA Guaranteed State"
      ],
      cta: "Request Demo",
      featured: false
    }
  ];

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-zinc-300 selection:bg-blue-500/30 font-sans overflow-x-hidden">
      <Navbar />

      <main className="relative z-10 pt-48 pb-32 px-6 max-w-6xl mx-auto">
        {/* Background glow effects */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-blue-500/10 blur-[120px] rounded-full pointer-events-none mix-blend-screen opacity-50" />
        
        <header className="text-center max-w-3xl mx-auto mb-32 relative z-10">
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-widest mb-8"
          >
            <Shield className="w-3.5 h-3.5" />
            Adaptive Pricing Architecture
          </motion.div>
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-5xl md:text-7xl font-bold tracking-tight mb-8 leading-[1.1] text-white"
          >
            Precision <br/><span className="text-zinc-500">costs nothing.</span>
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-xl text-zinc-400 max-w-xl mx-auto font-medium"
          >
            Scale your causal reasoning as your codebase grows. No hidden friction, just pure cognitive integrity.
          </motion.p>
        </header>

        {/* Pricing Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center mb-40 relative z-10">
          {plans.map((plan, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 + 0.3 }}
              className={`flex h-full ${plan.featured ? "md:-translate-y-4" : ""}`}
            >
              <SpotlightCard className={`p-10 rounded-[2.5rem] flex flex-col w-full transition-all duration-300 ${
                plan.featured 
                  ? "bg-[#111111] border border-blue-500/30 shadow-[0_0_80px_rgba(37,99,235,0.08)] relative z-20" 
                  : "bg-transparent border border-white/5 hover:bg-[#111111]/50"
              }`}>
                <div className="mb-10 text-center">
                  <div className="text-zinc-500 text-xs font-bold uppercase tracking-widest mb-6">{plan.name}</div>
                  <div className="flex items-baseline justify-center gap-2 mb-4">
                    <span className="text-5xl font-bold text-white tracking-tight">{plan.price}</span>
                    {plan.price !== "Contact" && <span className="text-sm text-zinc-500 font-medium">/cycle</span>}
                  </div>
                  <p className="text-zinc-400 text-sm">{plan.description}</p>
                </div>

                <div className="space-y-4 mb-10 flex-1">
                  {plan.features.map((feature, j) => (
                    <div key={j} className="flex items-center gap-3">
                      <div className={`w-1.5 h-1.5 rounded-full ${plan.featured ? "bg-blue-500" : "bg-zinc-600"}`} />
                      <span className="text-sm text-zinc-300">{feature}</span>
                    </div>
                  ))}
                </div>

                <Link 
                  to="/signup" 
                  className={`w-full py-4 rounded-xl font-semibold transition-all flex items-center justify-center gap-2 ${
                    plan.featured 
                      ? "bg-blue-600 text-white hover:bg-blue-500 shadow-xl shadow-blue-500/20 relative z-10 group" 
                      : "bg-white/5 text-white hover:bg-white/10 relative z-10"
                  }`}
                >
                  {plan.cta}
                  <ArrowRight className="w-4 h-4" />
                  {plan.featured && <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl" />}
                </Link>
              </SpotlightCard>
            </motion.div>
          ))}
        </div>

        {/* Security & Intelligence Features */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
           <SpotlightCard className="p-12 rounded-[3rem] bg-[#111111] border border-white/5 group">
              <Shield className="w-8 h-8 text-blue-500 mb-8" />
              <h2 className="text-2xl font-bold mb-4 text-white">Identity Isolation</h2>
              <p className="text-zinc-400 text-sm leading-relaxed mb-8">Your causal graph is yours alone. We use zero-knowledge state proofs to verify integrity without ever seeing your source.</p>
              <button className="text-blue-400 text-sm font-semibold flex items-center gap-2 group-hover:gap-4 transition-all relative z-10">
                 Security Manifesto <ChevronRight className="w-4 h-4" />
              </button>
           </SpotlightCard>

           <SpotlightCard className="p-12 rounded-[3rem] bg-[#111111] border border-white/5 group">
              <Cpu className="w-8 h-8 text-purple-500 mb-8" />
              <h2 className="text-2xl font-bold mb-4 text-white">Neural Credits</h2>
              <p className="text-zinc-400 text-sm leading-relaxed mb-8">Dynamically scale your inference power. Pay only for the depth of causal reasoning you actually execute.</p>
              <button className="text-purple-400 text-sm font-semibold flex items-center gap-2 group-hover:gap-4 transition-all relative z-10">
                 Usage Analytics <ChevronRight className="w-4 h-4" />
              </button>
           </SpotlightCard>
        </div>
      </main>

      <footer className="py-12 border-t border-white/5 text-center mt-32 relative z-10">
        <div className="flex items-center justify-center gap-2 mb-6">
           <div className="w-6 h-6 bg-white text-black rounded-md flex items-center justify-center font-black text-sm italic">Ω</div>
           <span className="font-bold tracking-tight text-white">HCR</span>
        </div>
        <p className="text-zinc-600 text-sm">© 2026 Panthera Labs. Intelligence is State.</p>
      </footer>
    </div>
  );
}

