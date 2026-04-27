"""
Neural Causal Operator (Φ_nc)

Discovers "Latent Causal Links" using LLM inference.
Identifies dependencies that static AST parsing misses (config files, env vars, etc.).
"""

from typing import Dict, Any, List, Optional
from .base_operator import BaseOperator, OperatorType
from ..state.cognitive_state import CognitiveState

CAUSAL_DISCOVERY_SYSTEM_PROMPT = """You are a causal reasoning engine for a software development environment.
Your task is to analyze project context and discover "Latent Causal Links"—dependencies that aren't obvious through simple imports.

Examples of Latent Causal Links:
1. "src/api.py -> config.yaml" (API reads config at runtime)
2. "src/db.py -> .env" (DB depends on environment variables)
3. "web/index.html -> src/styles.css" (HTML links CSS via <link> tag)
4. "src/app.py -> data/models/model.pt" (App loads a weights file)

Analyze the provided facts and file lists to infer these hidden connections.

Respond ONLY with valid JSON in this exact format:
{
    "latent_links": [
        {"cause": "path/to/file_a", "effect": "path/to/file_b", "type": "config|env|data|resource", "reason": "explanation"}
    ],
    "system_fragility": [
        {"file": "path/to/file", "risk": "low|medium|high", "reason": "explanation"}
    ]
}"""

class NeuralCausalOperator(BaseOperator):
    """
    Neural operator specialized in discovering latent causal relationships.
    Uses LLMs to bridge the gap between static analysis and logical system flow.
    """
    
    def __init__(
        self,
        operator_id: str,
        llm_provider=None,
        description: str = ""
    ):
        super().__init__(operator_id, OperatorType.NEURAL, description)
        self._llm = llm_provider

    def _execute(self, state: CognitiveState, **kwargs) -> Dict[str, Any]:
        """
        Discover latent links using LLM inference if available.
        """
        if not self._llm:
            return {"latent_links": [], "facts": ["warning:no_llm_for_causal_discovery"]}
            
        # Build prompt from state
        prompt = self._build_discovery_prompt(state)
        
        try:
            result = self._llm.structured_complete(
                prompt=prompt,
                system=CAUSAL_DISCOVERY_SYSTEM_PROMPT,
                temperature=0.2
            )
            
            if not result:
                return {"latent_links": [], "facts": ["error:causal_discovery_failed"]}
                
            latent_links = result.get("latent_links", [])
            fragility = result.get("system_fragility", [])
            
            # Format as symbolic facts for the engine
            facts = []
            for link in latent_links:
                facts.append(f"latent_link:{link['cause']}->{link['effect']} ({link['type']})")
                
            for risk in fragility:
                facts.append(f"risk_assessment:{risk['file']} is {risk['risk']} ({risk['reason']})")
                
            return {
                "latent_links": latent_links,
                "fragility": fragility,
                "facts": facts,
                "dependencies": [f"{l['cause']} -> {l['effect']}" for l in latent_links]
            }
        except Exception as e:
            return {"error": str(e), "facts": [f"error:causal_discovery_exception:{str(e)}"]}

    def _build_discovery_prompt(self, state: CognitiveState) -> str:
        """Construct prompt with current files and symbolic facts"""
        facts = "\n".join(state.symbolic.facts[-20:])
        # In a real scenario, we'd also pass recent file contents or file lists
        return f"""Current Symbolic Facts:
{facts}

Identify latent causal links and system fragility based on these facts and known project structure."""
