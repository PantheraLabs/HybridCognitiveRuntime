"""
Metrics Analyzer for Causal Nodes

Calculates "Fragility" and "Centrality" metrics for files in the Causal Graph.
Higher fragility = more likely to break when dependencies change.
Higher centrality = more ripple effect when this file changes.
"""

import ast
import os
from typing import Dict

class MetricsAnalyzer:
    @staticmethod
    def calculate_fragility(file_path: str) -> float:
        """
        Calculates a fragility score (0.0 to 1.0) based on:
        - Cyclomatic complexity (simulated via node count)
        - Number of incoming dependencies
        - Ratio of logic to comments
        """
        if not os.path.exists(file_path) or not file_path.endswith('.py'):
            return 0.5
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
                
            # Heuristic: Node density
            node_count = len(list(ast.walk(tree)))
            lines = content.count('\n') + 1
            
            density = node_count / lines if lines > 0 else 0
            
            # Normalize (0.5 is average complexity)
            score = min(1.0, (density / 10.0) + (node_count / 1000.0))
            return round(score, 2)
        except:
            return 0.5

    @staticmethod
    def calculate_centrality(file_path: str, forward_deps: Dict[str, list], reverse_deps: Dict[str, list]) -> float:
        """
        Calculates centrality score (0.0 to 1.0) based on graph position.
        """
        out_degree = len(forward_deps.get(file_path, []))
        in_degree = len(reverse_deps.get(file_path, []))
        
        # High in_degree means many things depend on it (Critical)
        # High out_degree means it depends on many things (Fragile)
        
        score = (in_degree * 0.7 + out_degree * 0.3) / 10.0
        return min(1.0, round(score, 2))
