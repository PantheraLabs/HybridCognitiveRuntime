#!/usr/bin/env python3
import sys
sys.path.insert(0, r"C:\Users\rishi\Documents\GitHub\HybridCognitiveRuntime")

from product.integrations.tools.output_synthesizer import OutputSynthesizer

s = OutputSynthesizer(engine=None)
llm = s._get_llm()
print("LLM type:", type(llm).__name__)

if llm:
    result = llm.structured_complete("Return JSON: {\"status\": \"ok\"}")
    print("Result:", result)
    print("Is dict:", isinstance(result, dict))
else:
    print("LLM is None")
