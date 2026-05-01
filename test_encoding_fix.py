#!/usr/bin/env python3
"""Quick test for encoding fix"""
import sys
sys.path.insert(0, '.')

from src.engine_api import HCREngine

print("Testing state save with potential unicode...")
engine = HCREngine('.')
engine.load_state()

# Try to save state
if engine._current_state:
    print(f"State has {len(engine._current_state.symbolic.facts)} facts")
    result = engine.save_state()
    print(f"Save result: {result}")
    if result:
        print("✅ State saved successfully - encoding fix working!")
    else:
        print("❌ State save failed - check errors above")
else:
    print("No state to save")
