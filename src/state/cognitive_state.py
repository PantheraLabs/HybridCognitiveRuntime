"""
Cognitive State Representation

State is NOT text. It is structured data representing the cognitive state of the system.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


@dataclass
class SymbolicState:
    """Symbolic component of cognitive state - facts, rules, constraints"""
    facts: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": self.facts,
            "rules": self.rules,
            "constraints": self.constraints
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SymbolicState':
        return cls(
            facts=data.get("facts", []),
            rules=data.get("rules", []),
            constraints=data.get("constraints", [])
        )


@dataclass
class CausalState:
    """Causal component of cognitive state - dependencies and effects"""
    dependencies: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependencies": self.dependencies,
            "effects": self.effects
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CausalState':
        return cls(
            dependencies=data.get("dependencies", []),
            effects=data.get("effects", [])
        )


@dataclass
class MetaState:
    """Meta component of cognitive state - confidence, uncertainty, timestamp"""
    confidence: float = 0.5
    uncertainty: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetaState':
        return cls(
            confidence=data.get("confidence", 0.5),
            uncertainty=data.get("uncertainty", 0.5),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
        )


@dataclass
class CognitiveState:
    """
    Complete cognitive state representation
    
    S = {
      latent: vector(n),
      symbolic: {facts, rules, constraints},
      causal: {dependencies, effects},
      meta: {confidence, uncertainty, timestamp}
    }
    """
    latent: List[float] = field(default_factory=list)
    symbolic: SymbolicState = field(default_factory=SymbolicState)
    causal: CausalState = field(default_factory=CausalState)
    meta: MetaState = field(default_factory=MetaState)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latent": self.latent,
            "symbolic": self.symbolic.to_dict(),
            "causal": self.causal.to_dict(),
            "meta": self.meta.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CognitiveState':
        return cls(
            latent=data.get("latent", []),
            symbolic=SymbolicState.from_dict(data.get("symbolic", {})),
            causal=CausalState.from_dict(data.get("causal", {})),
            meta=MetaState.from_dict(data.get("meta", {}))
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'CognitiveState':
        return cls.from_dict(json.loads(json_str))

    def copy(self) -> 'CognitiveState':
        """Create a deep copy of the state"""
        return CognitiveState(
            latent=self.latent.copy(),
            symbolic=SymbolicState(
                facts=self.symbolic.facts.copy(),
                rules=self.symbolic.rules.copy(),
                constraints=self.symbolic.constraints.copy()
            ),
            causal=CausalState(
                dependencies=self.causal.dependencies.copy(),
                effects=self.causal.effects.copy()
            ),
            meta=MetaState(
                confidence=self.meta.confidence,
                uncertainty=self.meta.uncertainty,
                timestamp=self.meta.timestamp
            )
        )
