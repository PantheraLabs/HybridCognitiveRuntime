"""
Neural Operator (Φ_n) — LLM-Powered

Handles ambiguity and pattern recognition using real LLM inference.
Replaces the simulated vector math with actual language model calls.
"""

from typing import Dict, Any, List, Optional
from .base_operator import BaseOperator, OperatorType
from ..state.cognitive_state import CognitiveState


# System prompt for the Neural Operator
NEURAL_SYSTEM_PROMPT = """You are a cognitive reasoning engine analyzing developer workflow state.
You receive structured facts about a developer's current project context and must infer:
1. What the developer is currently working on (a clear, specific task description)
2. Their likely intent (what they're trying to achieve)
3. A confidence score (0.0-1.0) in your inference

Respond ONLY with valid JSON in this exact format:
{
    "inferred_task": "specific description of current task",
    "intent": "what the developer is trying to achieve",
    "confidence": 0.85,
    "key_observations": ["observation 1", "observation 2"],
    "inferred_facts": ["fact_1", "fact_2"]
}"""


SIMILARITY_SYSTEM_PROMPT = """You are a cognitive reasoning engine comparing two developer workflow states.
Determine how semantically similar these two states are and whether the developer's context has meaningfully changed.

Respond ONLY with valid JSON:
{
    "similarity_score": 0.85,
    "changed": false,
    "summary": "brief description of what changed or stayed the same"
}"""


class NeuralOperator(BaseOperator):
    """
    Neural operator for pattern recognition and handling ambiguity.

    Uses real LLM inference to analyze developer context and infer intent.
    Falls back to heuristic analysis if no LLM provider is configured.
    """

    def __init__(
        self,
        operator_id: str,
        pattern_size: int = 128,
        pattern_detector=None,
        description: str = "",
        llm_provider=None,
    ):
        super().__init__(operator_id, OperatorType.NEURAL, description)
        self.pattern_size = pattern_size
        self.pattern_detector = pattern_detector
        self._llm = llm_provider

    def set_llm_provider(self, provider):
        """Set or update the LLM provider"""
        self._llm = provider

    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Execute neural pattern recognition on cognitive state.

        If an LLM provider is available, uses real inference.
        Otherwise, falls back to heuristic analysis.
        """
        if self._llm:
            return self._execute_with_llm(state, **kwargs)
        else:
            return self._execute_heuristic(state, **kwargs)

    def _execute_with_llm(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Execute using real LLM inference"""

        # Build context prompt from cognitive state
        prompt = self._build_context_prompt(state)

        try:
            result = self._llm.structured_complete(
                prompt=prompt,
                system=NEURAL_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=512,
            )

            if result is None:
                # JSON parsing failed, fall back to heuristic
                return self._execute_heuristic(state, **kwargs)

            # Transform LLM output into state update format
            facts = []
            dependencies = []

            # Add inferred task as fact
            if result.get("inferred_task"):
                facts.append(f"task:{result['inferred_task']}")

            # Add intent
            if result.get("intent"):
                facts.append(f"intent:{result['intent']}")

            # Add any inferred facts
            for fact in result.get("inferred_facts", []):
                facts.append(fact)

            # Add key observations as facts
            for obs in result.get("key_observations", []):
                facts.append(f"observation:{obs}")

            # Add dependency on LLM inference
            dependencies.append("llm_inference:neural_analysis")

            return {
                "facts": facts,
                "dependencies": dependencies,
            }

        except Exception as e:
            # On any LLM failure, fall back gracefully
            return self._execute_heuristic(state, **kwargs)

    def _build_context_prompt(self, state: CognitiveState) -> str:
        """Build a prompt from the current cognitive state"""
        lines = ["## Current Developer Context\n"]

        # Symbolic facts
        if state.symbolic.facts:
            lines.append("### Facts:")
            for fact in state.symbolic.facts[:20]:  # Limit to avoid token waste
                lines.append(f"- {fact}")

        # Rules
        if state.symbolic.rules:
            lines.append("\n### Active Rules:")
            for rule in state.symbolic.rules[:10]:
                lines.append(f"- {rule}")

        # Causal state
        if state.causal.dependencies:
            lines.append("\n### Dependencies:")
            for dep in state.causal.dependencies[:10]:
                lines.append(f"- {dep}")

        if state.causal.effects:
            lines.append("\n### Known Effects:")
            for effect in state.causal.effects[:10]:
                lines.append(f"- {effect}")

        # Meta
        lines.append(f"\n### Meta:")
        lines.append(f"- Confidence: {state.meta.confidence:.2f}")
        lines.append(f"- Uncertainty: {state.meta.uncertainty:.2f}")

        return "\n".join(lines)

    def _execute_heuristic(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Fallback heuristic analysis when no LLM is available.
        Lightweight pattern matching on symbolic facts.
        """
        facts = []
        dependencies = []

        # Infer from existing facts using keyword matching
        all_facts = " ".join(state.symbolic.facts).lower()

        if "test" in all_facts:
            facts.append("pattern_detected:testing_activity")
        if "fix" in all_facts or "bug" in all_facts:
            facts.append("pattern_detected:debugging_activity")
        if "implement" in all_facts or "add" in all_facts or "create" in all_facts:
            facts.append("pattern_detected:feature_development")
        if "refactor" in all_facts:
            facts.append("pattern_detected:refactoring")

        # Check file diversity
        edited_files = [f for f in state.symbolic.facts if f.startswith("edited:")]
        if len(edited_files) > 5:
            facts.append("pattern_detected:wide_scope_changes")
        elif len(edited_files) == 1:
            facts.append("pattern_detected:focused_editing")

        dependencies.append("heuristic_inference:pattern_matching")

        return {
            "facts": facts,
            "dependencies": dependencies,
        }


class SimilarityOperator(NeuralOperator):
    """
    Neural operator for computing semantic similarity between states.
    Uses LLM for semantic comparison, falls back to fact overlap analysis.
    """

    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """Compare current state with a reference state"""
        reference = kwargs.get("reference_state")
        threshold = kwargs.get("similarity_threshold", 0.7)

        if not reference:
            return {
                "facts": ["similarity:no_comparison_possible"],
                "dependencies": ["similarity_check:no_reference"],
            }

        if self._llm:
            return self._compare_with_llm(state, reference, threshold)
        else:
            return self._compare_heuristic(state, reference, threshold)

    def _compare_with_llm(
        self, state: CognitiveState, reference: CognitiveState, threshold: float
    ) -> Dict[str, Any]:
        """Use LLM for semantic state comparison"""
        prompt = (
            f"## State A (Current):\nFacts: {state.symbolic.facts[:15]}\n"
            f"Dependencies: {state.causal.dependencies[:10]}\n\n"
            f"## State B (Reference):\nFacts: {reference.symbolic.facts[:15]}\n"
            f"Dependencies: {reference.causal.dependencies[:10]}"
        )

        try:
            result = self._llm.structured_complete(
                prompt=prompt,
                system=SIMILARITY_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=256,
            )

            if result is None:
                return self._compare_heuristic(state, reference, threshold)

            score = result.get("similarity_score", 0.5)
            facts = [f"similarity_score:{score:.3f}"]

            if score >= threshold:
                facts.extend(["similarity:high", "pattern:match"])
            else:
                facts.extend(["similarity:low", "pattern:divergence"])

            if result.get("summary"):
                facts.append(f"comparison:{result['summary']}")

            return {
                "facts": facts,
                "dependencies": ["similarity_check:llm_comparison"],
            }

        except Exception:
            return self._compare_heuristic(state, reference, threshold)

    def _compare_heuristic(
        self, state: CognitiveState, reference: CognitiveState, threshold: float
    ) -> Dict[str, Any]:
        """Fallback: compare states using fact overlap (Jaccard similarity)"""
        current_facts = set(state.symbolic.facts)
        ref_facts = set(reference.symbolic.facts)

        if not current_facts and not ref_facts:
            similarity = 1.0
        elif not current_facts or not ref_facts:
            similarity = 0.0
        else:
            intersection = current_facts & ref_facts
            union = current_facts | ref_facts
            similarity = len(intersection) / len(union)

        facts = [f"similarity_score:{similarity:.3f}"]

        if similarity >= threshold:
            facts.extend(["similarity:high", "pattern:match"])
        else:
            facts.extend(["similarity:low", "pattern:divergence"])

        return {
            "facts": facts,
            "dependencies": ["similarity_check:jaccard"],
        }
