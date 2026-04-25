"""
Causal Operator (Φ_c)

Handles cause-effect reasoning and dependency tracking.
Operates on the causal component of state.
"""

from typing import Dict, Any, List, Optional, Tuple
from .base_operator import BaseOperator, OperatorType
from ..state.cognitive_state import CognitiveState


class CausalOperator(BaseOperator):
    """
    Causal operator for cause-effect reasoning and dependency analysis.
    """
    
    def __init__(
        self,
        operator_id: str,
        causal_rules: Optional[List[str]] = None,
        description: str = ""
    ):
        super().__init__(operator_id, OperatorType.CAUSAL, description)
        self.causal_rules = causal_rules or []
    
    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Execute causal reasoning.
        
        Args:
            **kwargs:
                - operation: type of causal operation
                    - predict: predict effects from causes
                    - explain: explain causes from effects
                    - trace: trace causal chain
                    - add_cause: add a cause-effect relationship
        """
        operation = kwargs.get("operation", "predict")
        
        if operation == "predict":
            return self._predict_effects(state, **kwargs)
        elif operation == "explain":
            return self._explain_causes(state, **kwargs)
        elif operation == "trace":
            return self._trace_chain(state, **kwargs)
        elif operation == "add_cause":
            return self._add_causal_link(state, **kwargs)
        else:
            return {"dependencies": [], "effects": []}
    
    def _predict_effects(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Predict effects based on current causes.
        
        Format of causal rules: "cause -> effect"
        """
        facts = state.symbolic.facts.copy()
        existing_effects = state.causal.effects.copy()
        all_rules = state.causal.dependencies.copy() + self.causal_rules
        
        predicted_effects = []
        
        for rule in all_rules:
            if "->" in rule:
                parts = rule.split("->")
                if len(parts) == 2:
                    cause = parts[0].strip()
                    effect = parts[1].strip()
                    
                    if cause in facts and effect not in existing_effects:
                        predicted_effects.append(effect)
                        predicted_effects.append(f"predicted_from:{cause}")
        
        return {
            "effects": predicted_effects,
            "dependencies": ["causal_prediction"],
            "facts": [f"effect:{e}" for e in predicted_effects]
        }
    
    def _explain_causes(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Explain what causes led to a given effect.
        """
        target_effect = kwargs.get("target_effect")
        all_rules = state.causal.dependencies.copy() + self.causal_rules
        
        if not target_effect:
            return {
                "dependencies": [],
                "facts": ["error:no_target_effect_specified"]
            }
        
        possible_causes = []
        
        for rule in all_rules:
            if "->" in rule:
                parts = rule.split("->")
                if len(parts) == 2:
                    cause = parts[0].strip()
                    effect = parts[1].strip()
                    
                    if effect == target_effect or target_effect in effect:
                        possible_causes.append(cause)
        
        return {
            "dependencies": possible_causes,
            "facts": [f"explanation:cause_of_{target_effect}={c}" for c in possible_causes] if possible_causes else [f"explanation:no_cause_found_for_{target_effect}"]
        }
    
    def _trace_chain(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Trace a causal chain from a starting cause.
        """
        start_cause = kwargs.get("start_cause")
        max_depth = kwargs.get("max_depth", 5)
        all_rules = state.causal.dependencies.copy() + self.causal_rules
        
        if not start_cause:
            return {
                "dependencies": [],
                "facts": ["error:no_start_cause_specified"]
            }
        
        chain = self._build_causal_chain(start_cause, all_rules, max_depth)
        
        return {
            "dependencies": chain,
            "facts": [f"causal_chain:{start_cause}->{'->'.join(chain)}"]
        }
    
    def _build_causal_chain(
        self,
        start: str,
        rules: List[str],
        max_depth: int,
        current_depth: int = 0
    ) -> List[str]:
        """Recursively build a causal chain"""
        if current_depth >= max_depth:
            return []
        
        chain = []
        
        for rule in rules:
            if "->" in rule:
                parts = rule.split("->")
                if len(parts) == 2:
                    cause = parts[0].strip()
                    effect = parts[1].strip()
                    
                    if cause == start and effect not in chain:
                        chain.append(effect)
                        # Recursively trace from this effect
                        sub_chain = self._build_causal_chain(effect, rules, max_depth, current_depth + 1)
                        chain.extend(sub_chain)
        
        return chain
    
    def _add_causal_link(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Add a new cause-effect relationship"""
        cause = kwargs.get("cause")
        effect = kwargs.get("effect")
        
        if not cause or not effect:
            return {
                "dependencies": [],
                "facts": ["error:missing_cause_or_effect"]
            }
        
        causal_link = f"{cause} -> {effect}"
        
        return {
            "dependencies": [causal_link],
            "effects": [effect],
            "facts": [f"causal_link_added:{causal_link}"]
        }


class DependencyOperator(CausalOperator):
    """
    Specialized operator for dependency analysis.
    """
    
    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Analyze dependencies in the current state.
        
        Args:
            **kwargs:
                - operation: identify_dependencies, check_cycles, find_roots
        """
        operation = kwargs.get("operation", "identify_dependencies")
        
        if operation == "identify_dependencies":
            return self._identify_all_dependencies(state, **kwargs)
        elif operation == "check_cycles":
            return self._check_cyclic_dependencies(state, **kwargs)
        elif operation == "find_roots":
            return self._find_root_causes(state, **kwargs)
        
        return {"dependencies": [], "effects": []}
    
    def _identify_all_dependencies(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Identify all dependencies in the current state"""
        all_deps = state.causal.dependencies.copy()
        
        return {
            "dependencies": all_deps,
            "facts": [f"dependency:{d}" for d in all_deps]
        }
    
    def _check_cyclic_dependencies(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Check for cycles in causal dependencies"""
        all_rules = state.causal.dependencies.copy()
        cycles = []
        
        # Simple cycle detection
        for rule in all_rules:
            if "->" in rule:
                parts = rule.split("->")
                if len(parts) == 2:
                    cause = parts[0].strip()
                    effect = parts[1].strip()
                    
                    # Check if effect can reach back to cause
                    if self._can_reach(effect, cause, all_rules, set()):
                        cycles.append(f"cycle:{cause}->{effect}->{cause}")
        
        return {
            "dependencies": [],
            "effects": cycles,
            "facts": cycles if cycles else ["cycles:none_found"]
        }
    
    def _can_reach(
        self,
        start: str,
        target: str,
        rules: List[str],
        visited: set
    ) -> bool:
        """Check if start can reach target through causal chain"""
        if start in visited:
            return False
        
        visited.add(start)
        
        for rule in rules:
            if "->" in rule:
                parts = rule.split("->")
                if len(parts) == 2:
                    cause = parts[0].strip()
                    effect = parts[1].strip()
                    
                    if cause == start:
                        if effect == target:
                            return True
                        if self._can_reach(effect, target, rules, visited):
                            return True
        
        return False
    
    def _find_root_causes(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Find root causes (causes that are not effects of anything else)"""
        all_rules = state.causal.dependencies.copy()
        
        all_causes = set()
        all_effects = set()
        
        for rule in all_rules:
            if "->" in rule:
                parts = rule.split("->")
                if len(parts) == 2:
                    all_causes.add(parts[0].strip())
                    all_effects.add(parts[1].strip())
        
        # Roots are causes that are never effects
        roots = all_causes - all_effects
        
        return {
            "dependencies": list(roots),
            "facts": [f"root_cause:{r}" for r in roots]
        }
