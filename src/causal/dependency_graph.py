"""
Dependency Graph

An in-memory directed graph representing file and functional dependencies
derived from the AST and causal events.
"""

from typing import Dict, List, Set
from pathlib import Path

class DependencyGraph:
    def __init__(self):
        # Maps a node (file path or module) to a list of nodes it depends on
        self.forward_edges: Dict[str, Set[str]] = {}
        # Maps a node to a list of nodes that depend on it
        self.reverse_edges: Dict[str, Set[str]] = {}
        # Latent links discovered by LLM (cause, effect, type, reason)
        self.latent_edges: List[dict] = []

    def add_dependency(self, source: str, target: str):
        """Add a directed edge from source to target (source depends on target)."""
        if source not in self.forward_edges:
            self.forward_edges[source] = set()
        self.forward_edges[source].add(target)

        if target not in self.reverse_edges:
            self.reverse_edges[target] = set()
        self.reverse_edges[target].add(source)

    def add_latent_link(self, source: str, target: str, link_type: str = "latent", reason: str = ""):
        """Add a latent link discovered by neural inference."""
        self.latent_edges.append({
            "source": source,
            "target": target,
            "type": link_type,
            "reason": reason
        })
        # Also add to standard graph for impact analysis
        self.add_dependency(source, target)

    def get_metrics(self, node: str) -> dict:
        """Calculate and return metrics for a specific node"""
        from .metrics import MetricsAnalyzer
        fragility = MetricsAnalyzer.calculate_fragility(node)
        centrality = MetricsAnalyzer.calculate_centrality(
            node, 
            self.forward_edges, 
            self.reverse_edges
        )
        return {
            "fragility": fragility,
            "centrality": centrality,
            "risk_score": round((fragility + centrality) / 2, 2)
        }

    def to_dict(self) -> dict:
        """Convert graph to dictionary with node metrics and latent links"""
        nodes = list(set(list(self.forward_edges.keys()) + list(self.reverse_edges.keys())))
        node_data = {node: self.get_metrics(node) for node in nodes}
        
        return {
            "forward": self.forward_edges,
            "reverse": self.reverse_edges,
            "latent_links": self.latent_edges,
            "metrics": node_data
        }

    def get_dependencies(self, node: str) -> List[str]:
        """Get all nodes that the given node depends on."""
        return list(self.forward_edges.get(node, set()))

    def get_dependents(self, node: str) -> List[str]:
        """Get all nodes that depend on the given node."""
        return list(self.reverse_edges.get(node, set()))

    def update_file_dependencies(self, file_path: str, dependencies: List[str]):
        """Replace existing dependencies for a file with a new set."""
        # Remove old forward edges
        old_deps = self.forward_edges.get(file_path, set())
        for target in old_deps:
            if file_path in self.reverse_edges.get(target, set()):
                self.reverse_edges[target].remove(file_path)
                
        # Set new dependencies
        self.forward_edges[file_path] = set()
        for target in dependencies:
            self.add_dependency(file_path, target)
