"""
HCR Causal Intelligence Package

The Temporal Causal Graph — HCR's core moat.
Tracks file dependencies, temporal event chains, and predicts impact.
"""

from .dependency_graph import DependencyGraph
from .event_store import EventStore, CausalEvent
from .impact_analyzer import ImpactAnalyzer
