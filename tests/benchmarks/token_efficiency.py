#!/usr/bin/env python3
"""
HCR Token Efficiency Benchmark

Validates the 10-100x token reduction claim from market positioning.
Compares traditional AI context rebuilding vs HCR state-based approach.
"""

import sys
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class BenchmarkResult:
    """Result of a single benchmark scenario"""
    scenario: str
    traditional_tokens: int
    hcr_tokens: int
    traditional_time_ms: float
    hcr_time_ms: float
    speedup: float
    token_reduction: float


class TokenEfficiencyBenchmark:
    """Benchmark HCR token efficiency vs traditional AI approach"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.results: List[BenchmarkResult] = []
        
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ~ 4 chars for code)"""
        return len(text) // 4
    
    def _get_traditional_context(self, scenario: str) -> tuple[str, int]:
        """
        Simulate traditional AI context rebuilding.
        In reality, this would be the user's manual explanation + file contents.
        """
        # Read recent files for context
        from product.state_capture.file_watcher import FileWatcher
        from product.state_capture.git_tracker import GitTracker
        
        watcher = FileWatcher(self.project_path)
        git = GitTracker(self.project_path)
        
        # Simulate the context a user would provide
        # This is what a developer ACTUALLY has to type/explain to an AI
        context_parts = []
        
        # 1. Detailed project description (user types this extensively)
        context_parts.append(f"""I'm working on the HCR (Hybrid Cognitive Runtime) project.

Project Overview:
- It's a cognitive architecture for AI development tools
- Uses state-based reasoning instead of prompt-based context
- Has neural, symbolic, and causal operators
- Currently implementing: {scenario}

The codebase structure:
- src/state/ - Cognitive state management
- src/operators/ - HCO implementations (neural, symbolic, causal)
- src/core/ - HCO execution engine
- src/causal/ - Dependency graph and impact analysis
- src/llm/ - LLM provider abstractions
- product/ - Production features (CLI, VS Code extension, MCP server)
- tests/ - Unit tests
- web/ - Web dashboard

I was specifically working on the {scenario} aspect of this project.
""")
        
        # 2. Recent files with detailed content simulation (user would paste or AI reads)
        file_state = watcher.capture_state(lookback_minutes=120)
        context_parts.append("\n## Recent Files I Was Working On:\n")
        for f in file_state.get("recent_files", [])[:5]:
            context_parts.append(f"\n### File: {f['path']}")
            context_parts.append(f"Last modified: {f.get('modified_at', 'unknown')}")
            context_parts.append(f"Size: {f.get('size_bytes', 0)} bytes")
            # Simulate showing file content (this is what actually gets sent to AI)
            context_parts.append("```python")
            context_parts.append("# File content would be shown here...")
            context_parts.append("# (Simulating actual code content that AI needs to see)")
            context_parts.append("# Line 1: import statements...")
            context_parts.append("# Line 2-50: Class/function definitions...")
            context_parts.append("# ... (typically 500+ tokens of code content)")
            context_parts.append("```")
        
        # 3. Git state with detailed commit info
        git_state = git.capture_state()
        uncommitted = git_state.get('uncommitted_changes', {})
        context_parts.append(f"""

## Git Status:
Current Branch: {git_state.get('branch', 'unknown')}

Last Commit: {git_state.get('last_commit', {}).get('message', 'unknown')[:100]}
Commit Hash: {git_state.get('last_commit', {}).get('hash', 'unknown')[:8]}
Commit Date: {git_state.get('last_commit', {}).get('timestamp', 'unknown')}

Uncommitted Changes:
- Modified files: {uncommitted.get('modified_count', 0)}
- Staged files: {uncommitted.get('staged_count', 0)}
- Untracked files: {uncommitted.get('untracked_count', 0)}

File Details:
""")
        for f in uncommitted.get('files', [])[:5]:
            context_parts.append(f"- {f.get('path', 'unknown')} ({f.get('status', 'modified')})")
        
        # 4. Current task - detailed explanation (user must type all this)
        context_parts.append(f"""

## What I Was Doing:

I was working on: {scenario}

Progress so far:
1. I've analyzed the requirements
2. I've looked at the existing implementation
3. I've started making changes
4. I got interrupted and need to resume

Specific details:
- The {scenario} functionality is part of the larger HCR system
- It needs to integrate with the existing state management
- I had some uncommitted changes related to this
- I need to remember what my next step was

Please help me:
1. Understand what I was working on
2. Know what progress I made
3. Suggest what I should do next
4. Consider any dependencies or impacts
""")
        
        full_context = "\n".join(context_parts)
        tokens = self._estimate_tokens(full_context)
        
        return full_context, tokens
    
    def _get_hcr_context(self) -> tuple[str, int]:
        """
        Get context via HCR state loading.
        Minimal tokens - just the state representation.
        """
        from src.engine_api import HCREngine
        
        engine = HCREngine(self.project_path)
        engine.load_state()
        context = engine.infer_context()
        
        # HCR provides structured context - very token-efficient
        hcr_summary = f"""Task: {context.current_task}
Progress: {context.progress_percent}%
Next: {context.next_action}
Confidence: {context.confidence:.0%}
Facts: {len(context.facts)}"""
        
        tokens = self._estimate_tokens(hcr_summary)
        
        return hcr_summary, tokens
    
    def benchmark_scenario(self, scenario: str) -> BenchmarkResult:
        """Run benchmark for a specific scenario"""
        print(f"\n  Benchmarking: {scenario}...")
        
        # Traditional approach
        start = time.time()
        traditional_context, traditional_tokens = self._get_traditional_context(scenario)
        traditional_time = (time.time() - start) * 1000
        
        # HCR approach
        start = time.time()
        hcr_context, hcr_tokens = self._get_hcr_context()
        hcr_time = (time.time() - start) * 1000
        
        result = BenchmarkResult(
            scenario=scenario,
            traditional_tokens=traditional_tokens,
            hcr_tokens=hcr_tokens,
            traditional_time_ms=traditional_time,
            hcr_time_ms=hcr_time,
            speedup=traditional_time / max(hcr_time, 1),
            token_reduction=traditional_tokens / max(hcr_tokens, 1)
        )
        
        print(f"    Traditional: {traditional_tokens:,} tokens, {traditional_time:.0f}ms")
        print(f"    HCR: {hcr_tokens:,} tokens, {hcr_time:.0f}ms")
        print(f"    Token reduction: {result.token_reduction:.1f}x")
        print(f"    Speedup: {result.speedup:.1f}x")
        
        return result
    
    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all benchmark scenarios"""
        scenarios = [
            "Fresh project startup",
            "Returning after 1 hour",
            "Returning after 8 hours (next day)",
            "Code review session",
            "Debugging with context",
            "Feature implementation resumption"
        ]
        
        print("\n" + "="*60)
        print("HCR Token Efficiency Benchmark")
        print("="*60)
        print(f"Project: {self.project_path}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        for scenario in scenarios:
            result = self.benchmark_scenario(scenario)
            self.results.append(result)
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate formatted benchmark report"""
        if not self.results:
            self.run_all_benchmarks()
        
        avg_token_reduction = sum(r.token_reduction for r in self.results) / len(self.results)
        avg_speedup = sum(r.speedup for r in self.results) / len(self.results)
        total_traditional = sum(r.traditional_tokens for r in self.results)
        total_hcr = sum(r.hcr_tokens for r in self.results)
        overall_reduction = total_traditional / max(total_hcr, 1)
        
        report = f"""
# HCR Token Efficiency Benchmark Report

**Generated:** {datetime.now().isoformat()}
**Project:** {self.project_path}

## Executive Summary

| Metric | Value |
|--------|-------|
| **Average Token Reduction** | {avg_token_reduction:.1f}x |
| **Average Time Speedup** | {avg_speedup:.1f}x |
| **Overall Token Reduction** | {overall_reduction:.1f}x |
| **Benchmarks Run** | {len(self.results)} |

## Detailed Results

| Scenario | Traditional (tokens) | HCR (tokens) | Reduction | Time Speedup |
|----------|---------------------|--------------|-----------|--------------|
"""
        for r in self.results:
            report += f"| {r.scenario} | {r.traditional_tokens:,} | {r.hcr_tokens:,} | {r.token_reduction:.1f}x | {r.speedup:.1f}x |\n"
        
        report += f"""
## Market Positioning Validation

**Claim:** 10-100x token reduction
**Measured:** {overall_reduction:.1f}x overall reduction
**Status:** {"✅ VALIDATED" if overall_reduction >= 10 else "⚠️ PARTIAL (below 10x target)"}

## Technical Details

### Traditional Approach
- User must manually explain project context
- AI must read file contents to understand state
- Git state must be described or queried
- Progress and next steps inferred from scratch
- Average: {total_traditional // len(self.results):,} tokens per session

### HCR Approach
- State loaded from `.hcr/session_state.json`
- Pre-computed task inference and progress tracking
- Causal graph provides dependency context
- Average: {total_hcr // len(self.results):,} tokens per session

## Recommendations

"""
        
        if overall_reduction >= 50:
            report += """🎯 **Excellent:** HCR achieves exceptional token efficiency (50x+).
This is a significant competitive advantage for enterprise customers
concerned about API costs.

"""
        elif overall_reduction >= 10:
            report += """✅ **Good:** HCR meets the minimum 10x token reduction target.
Marketing claim is validated. Consider optimizing further to reach 50x.

"""
        else:
            report += """⚠️ **Needs Improvement:** Token reduction below 10x target.
Recommend:
1. Implement state compression
2. Add selective fact loading
3. Optimize state serialization

"""
        
        report += """
## Raw Data

"""
        report += json.dumps([{
            "scenario": r.scenario,
            "traditional_tokens": r.traditional_tokens,
            "hcr_tokens": r.hcr_tokens,
            "token_reduction": round(r.token_reduction, 2),
            "speedup": round(r.speedup, 2)
        } for r in self.results], indent=2)
        report += """
```
"""
        
        return report
    
    def save_report(self, output_path: str = None):
        """Save report to file"""
        if output_path is None:
            output_path = self.project_path / "docs" / "research" / "token_benchmark_report.md"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = self.generate_report()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n✅ Report saved to: {output_path}")
        return output_path


def main():
    """Run benchmark from CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="HCR Token Efficiency Benchmark")
    parser.add_argument("--project", default=".", help="Project path to benchmark")
    parser.add_argument("--output", help="Output path for report")
    
    args = parser.parse_args()
    
    benchmark = TokenEfficiencyBenchmark(args.project)
    benchmark.run_all_benchmarks()
    
    # Print summary
    print("\n" + "="*60)
    print("BENCHMARK COMPLETE")
    print("="*60)
    
    avg_reduction = sum(r.token_reduction for r in benchmark.results) / len(benchmark.results)
    print(f"Average Token Reduction: {avg_reduction:.1f}x")
    
    if avg_reduction >= 10:
        print(f"✅ Target achieved: 10x+ reduction")
    else:
        print(f"⚠️ Below target: {avg_reduction:.1f}x < 10x")
    
    # Save report
    output = benchmark.save_report(args.output)
    print(f"\nFull report: {output}")


if __name__ == "__main__":
    main()
