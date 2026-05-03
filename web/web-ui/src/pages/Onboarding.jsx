import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  PlayCircle,
  Terminal,
  Settings,
  Cpu,
  Activity,
  CheckCircle2,
  Zap,
  Boxes,
  Shield,
  Layers,
  ClipboardCheck
} from 'lucide-react';
import Navbar from '../components/Navbar';

const setupSteps = [
  {
    title: 'Install & Verify',
    description: 'Bootstrap HCR locally and ensure dependencies are satisfied.',
    command: 'pip install -e .\npython -m product.cli.main doctor'
  },
  {
    title: 'Capture Context',
    description: 'Initialize project memory and start the daemon.',
    command: 'hcr init --auto\nhcr daemon start --project /path/to/repo'
  },
  {
    title: 'Connect MCP Clients',
    description: 'Expose the HCR MCP server to Cursor, Windsurf, or Claude Desktop.',
    command: 'python mcp_server_wrapper.py --port 3323'
  },
  {
    title: 'Log First Activity',
    description: 'Open your IDE, edit a file, and let HCR record the causal graph.',
    command: 'hcr capture-full-context --include-diffs false'
  }
];

const ideCards = [
  {
    name: 'Cursor',
    accent: 'bg-blue-500/20 border-blue-400/30',
    steps: [
      'Settings → Experimental → MCP Servers',
      'Add new endpoint pointing to http://localhost:3323',
      'Paste the AI IDE global rule-set from docs/MCP_TOOLS_USAGE_GUIDE.md'
    ]
  },
  {
    name: 'Windsurf / Cascade',
    accent: 'bg-purple-500/10 border-purple-300/20',
    steps: [
      'Open .windsurf/config.json',
      'Add HCR MCP server definition with tool namespace `hcr_*`',
      'Drop the rule-set into .windsurf/rules.md'
    ]
  },
  {
    name: 'Claude Desktop',
    accent: 'bg-emerald-500/10 border-emerald-300/20',
    steps: [
      'Preferences → Integrations → MCP Servers',
      'Point to the same localhost port',
      'Enable "Auto tools" so HCR state is always referenced'
    ]
  }
];

const tourMoments = [
  {
    title: 'Welcome Pulse',
    description: 'Detects first project load, surfaces current git branch, open files, and last HCR task automatically.',
    icon: Activity
  },
  {
    title: 'Timeline Wizard',
    description: 'Guides users through initializing `.hcr/`, launching the daemon, and registering their IDE.',
    icon: Layers
  },
  {
    title: 'Context Proof',
    description: 'Runs the capture_full_context tool so they can watch HCR resurrect the previous session in real time.',
    icon: CheckCircle2
  },
  {
    title: 'Security Check',
    description: 'Explains where state lives on disk, how to rotate keys, and how cross-project sharing is gated.',
    icon: Shield
  }
];

export default function Onboarding() {
  const [selectedStep, setSelectedStep] = useState(0);
  const [copiedIndex, setCopiedIndex] = useState(null);

  const handleCopy = async (command, index) => {
    try {
      await navigator.clipboard.writeText(command);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error('Clipboard copy failed', err);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] text-zinc-200">
      <Navbar />

      <section className="pt-36 pb-20 px-6 bg-gradient-to-b from-[#050505] via-[#080808] to-[#050505]">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1 rounded-full border border-white/10 text-xs uppercase tracking-[0.3em] text-zinc-400">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Guided Mode v1
          </div>
          <h1 className="text-5xl md:text-6xl font-black tracking-tight text-white mt-8 mb-6">
            Ship-ready onboarding, no context loss.
          </h1>
          <p className="text-lg text-zinc-400 max-w-3xl mx-auto mb-10">
            This flow mirrors commercial SaaS tours: a cinematic welcome, deterministic setup wizard, copy-paste CLI snippets, and IDE-specific guidance so teams are productive in minutes.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/app" className="px-8 py-4 bg-white text-black font-semibold rounded-2xl flex items-center justify-center gap-2 shadow-xl">
              Launch Console <ArrowRight className="w-4 h-4" />
            </Link>
            <a href="#setup" className="px-8 py-4 border border-white/20 rounded-2xl text-white flex items-center justify-center gap-2 hover:bg-white/5">
              Watch Guided Setup <PlayCircle className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      <section id="setup" className="px-6 py-24 border-y border-white/5 bg-[#060606]">
        <div className="max-w-6xl mx-auto grid lg:grid-cols-[1.2fr_0.8fr] gap-12">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-blue-300 mb-6">Step-by-step timeline</p>
            <div className="space-y-6">
              {setupSteps.map((step, index) => (
                <button
                  key={step.title}
                  onClick={() => setSelectedStep(index)}
                  className={`w-full text-left rounded-3xl border transition-all p-6 bg-[#0A0A0A] hover:border-white/30 ${
                    index === selectedStep ? 'border-white/40 shadow-[0_20px_80px_rgba(59,130,246,0.15)]' : 'border-white/10'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-zinc-400 text-xs">Phase {index + 1}</div>
                    {index === selectedStep && (
                      <span className="text-emerald-300 text-xs inline-flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> highlighted</span>
                    )}
                  </div>
                  <h3 className="text-white text-xl font-semibold mb-2">{step.title}</h3>
                  <p className="text-zinc-400 text-sm">{step.description}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-gradient-to-b from-[#0F0F0F] to-[#080808] p-8">
            <p className="text-sm uppercase tracking-[0.3em] text-zinc-500 mb-4 flex items-center gap-2">
              <Terminal className="w-4 h-4" /> Commands
            </p>
            <div className="bg-black/60 border border-white/5 rounded-2xl p-6 font-mono text-sm text-zinc-300 whitespace-pre-wrap relative">
              {setupSteps[selectedStep].command}
              <button
                onClick={() => handleCopy(setupSteps[selectedStep].command, selectedStep)}
                className="absolute top-4 right-4 text-xs px-3 py-1 border border-white/20 rounded-full text-white hover:bg-white/10"
              >
                {copiedIndex === selectedStep ? 'Copied' : 'Copy'}
              </button>
            </div>
            <div className="mt-6 text-zinc-500 text-xs flex items-center gap-2">
              <ClipboardCheck className="w-3.5 h-3.5" /> All commands are safe to run locally; no cloud dependency.
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-24 bg-[#050505]">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-12">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-purple-300 mb-3">IDE integrations</p>
              <h2 className="text-4xl font-black text-white">Commercial-grade client coverage.</h2>
              <p className="text-zinc-500 max-w-2xl">Every onboarding run shows exactly how to wire up the MCP server per IDE, including rule placement and health checks.</p>
            </div>
            <Link to="/docs" className="text-zinc-400 text-sm underline underline-offset-4">Read integration playbook →</Link>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {ideCards.map((card) => (
              <div key={card.name} className={`rounded-3xl border ${card.accent} p-6 backdrop-blur-xl`}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-white text-xl font-semibold">{card.name}</h3>
                  <Zap className="w-4 h-4 text-white/70" />
                </div>
                <ul className="space-y-3 text-sm text-zinc-300">
                  {card.steps.map((item) => (
                    <li key={item} className="flex gap-3">
                      <span className="text-blue-300">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-24 border-t border-white/5 bg-[#060606]">
        <div className="max-w-5xl mx-auto">
          <p className="text-sm uppercase tracking-[0.3em] text-emerald-300 mb-6">Guided tour moments</p>
          <div className="grid md:grid-cols-2 gap-6">
            {tourMoments.map(({ title, description, icon: Icon }) => (
              <div key={title} className="rounded-3xl border border-white/10 bg-[#0A0A0A] p-6 flex gap-4">
                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center">
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-xl text-white font-semibold mb-2">{title}</h3>
                  <p className="text-sm text-zinc-400">{description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 py-24 bg-[#050505]">
        <div className="max-w-5xl mx-auto rounded-[3rem] border border-white/10 p-12 text-center bg-gradient-to-b from-[#0F0F0F] to-[#050505]">
          <p className="text-sm uppercase tracking-[0.3em] text-blue-300 mb-4">Ready to launch?</p>
          <h2 className="text-4xl md:text-5xl font-black text-white mb-6">Add HCR onboarding to your next sprint.</h2>
          <p className="text-zinc-400 text-lg mb-10">Developers land, authenticate, provision the daemon, and resume coding in under five minutes. No more tribal knowledge handoffs.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/signup" className="px-8 py-4 bg-white text-black rounded-2xl font-semibold flex items-center justify-center gap-2">
              Secure Access <ArrowRight className="w-4 h-4" />
            </Link>
            <a href="https://github.com/PantheraLabs/HybridCognitiveRuntime" className="px-8 py-4 border border-white/20 rounded-2xl text-white flex items-center justify-center gap-2">
              View Repo <Boxes className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      <footer className="py-12 border-t border-white/5 text-center text-zinc-500 text-sm">
        Built by Panthera Labs · Intelligence is State.
      </footer>
    </div>
  );
}
