import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Activity } from 'lucide-react';

export default function Navbar() {
  return (
    <div className="fixed top-0 left-0 right-0 z-[100] flex justify-center p-8 pointer-events-none">
      <nav className="w-full max-w-7xl h-16 glass-panel rounded-3xl flex items-center justify-between px-8 pointer-events-auto shadow-2xl overflow-hidden">
        {/* Logo Section */}
        <Link to="/" className="flex items-center gap-4 group">
          <div className="w-9 h-9 bg-white text-black rounded-xl flex items-center justify-center font-black text-2xl transition-all group-hover:scale-105 group-hover:shadow-[0_0_20px_rgba(255,255,255,0.2)] italic">Ω</div>
          <span className="font-black tracking-tighter text-2xl text-white italic serif-display">HCR</span>
        </Link>
        
        {/* Navigation Links */}
        <div className="hidden md:flex items-center gap-10 mono-ui text-slate-500">
          <a href="/#features" className="hover:text-white transition-colors">Causal Map</a>
          <Link to="/pricing" className="hover:text-white transition-colors">Tiers</Link>
          <Link to="/onboarding" className="hover:text-white transition-colors">Onboarding</Link>
          <a href="https://github.com" className="hover:text-white transition-colors">Git</a>
          <div className="flex items-center gap-2 text-blue-500/50">
             <Activity className="w-3 h-3" />
             <span className="text-[8px]">Live v2.4</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-8">
          <Link to="/login" className="mono-ui text-slate-500 hover:text-white transition-colors">Connect</Link>
          <Link to="/app" className="bg-white text-black h-10 px-6 rounded-2xl mono-ui text-[11px] font-black hover:bg-blue-500 hover:text-white transition-all active:scale-95 flex items-center gap-3 group shadow-xl shadow-white/5">
            Console
            <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>
      </nav>
    </div>
  );
}
