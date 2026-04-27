import React from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowRight, 
  Mail, 
  Lock, 
  ChevronLeft
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function Auth() {
  const isLogin = window.location.pathname === '/login';

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex flex-col items-center justify-center p-6 font-sans relative overflow-hidden">
      
      {/* Absolute Header Navigation */}
      <div className="absolute top-8 left-8">
         <Link to="/" className="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-300 transition-colors font-medium text-sm">
            <ChevronLeft className="w-4 h-4" />
            Back to Home
         </Link>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-[420px]"
      >
        <div className="flex flex-col items-center mb-10 text-center">
           <Link to="/" className="flex items-center justify-center w-12 h-12 bg-white rounded-xl text-black font-black text-2xl italic shadow-md mb-8">
              Ω
           </Link>
           <h1 className="text-3xl font-bold text-white tracking-tight mb-3">
              {isLogin ? 'Welcome back' : 'Create your account'}
           </h1>
           <p className="text-zinc-400 font-medium text-sm max-w-[280px]">
              {isLogin ? 'Continue your session securely.' : 'Connect your identity to the runtime.'}
           </p>
        </div>

        <div className="bg-[#111111] border border-white/5 rounded-3xl p-8 shadow-2xl">
           <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>
              
              <button className="w-full h-12 bg-white hover:bg-zinc-100 text-black font-semibold rounded-xl flex items-center justify-center gap-3 transition-all active:scale-[0.98]">
                 <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                 </svg>
                 Continue with GitHub
              </button>

              <div className="relative flex items-center py-2">
                <div className="flex-grow border-t border-white/5"></div>
                <span className="flex-shrink mx-4 text-zinc-600 text-xs font-medium uppercase tracking-widest">Or</span>
                <div className="flex-grow border-t border-white/5"></div>
              </div>

              <div className="space-y-4">
                 <div>
                    <label className="text-zinc-400 text-sm font-medium block mb-2">Work Email</label>
                    <div className="relative">
                      <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                      <input 
                        type="email" 
                        placeholder="you@company.com"
                        className="w-full h-12 bg-white/[0.02] border border-white/10 rounded-xl pl-11 pr-4 text-white text-sm focus:bg-white/[0.04] focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 focus:outline-none transition-all"
                      />
                    </div>
                 </div>

                 <div>
                    <label className="text-zinc-400 text-sm font-medium block mb-2">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                      <input 
                        type="password" 
                        placeholder="••••••••"
                        className="w-full h-12 bg-white/[0.02] border border-white/10 rounded-xl pl-11 pr-4 text-white text-sm focus:bg-white/[0.04] focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 focus:outline-none transition-all"
                      />
                    </div>
                 </div>
              </div>

              <button className="w-full h-12 mt-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-all active:scale-[0.98] flex items-center justify-center gap-2">
                 {isLogin ? 'Sign in' : 'Create account'}
                 <ArrowRight className="w-4 h-4" />
              </button>
           </form>
        </div>

        <p className="text-center text-zinc-500 text-sm mt-8">
           {isLogin ? "Don't have an account? " : "Already have an account? "}
           <Link to={isLogin ? "/signup" : "/login"} className="text-zinc-300 hover:text-white transition-colors">
              {isLogin ? 'Sign up' : 'Sign in'}
           </Link>
        </p>

      </motion.div>
    </div>
  );
}
