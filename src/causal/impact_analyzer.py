"""
Impact Analyzer

Uses the Dependency Graph to predict the "ripple effect" of changes.
If file A is modified, what other files might be affected?
"""

from typing import List, Set
from .dependency_graph import DependencyGraph

class ImpactAnalyzer:
    def __init__(self, graph: DependencyGraph):
        self.graph = graph

    def predict_impact(self, modified_node: str, max_depth: int = 3) -> List[str]:
        """
        Predict which nodes will be impacted by a change to the modified_node.
        Traverses the reverse dependencies (nodes that depend on the modified_node).
        """
        impacted: Set[str] = set()
        
        def traverse(node: str, current_depth: int):
            if current_depth > max_depth:
                return
            
            dependents = self.graph.get_dependents(node)
            for dep in dependents:
                if dep not in impacted:
                    impacted.add(dep)
                    traverse(dep, current_depth + 1)
                    
        traverse(modified_node, 1)
        return list(impacted)
