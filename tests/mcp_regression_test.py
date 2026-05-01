"""
MCP Tool Regression Test
Validates that previously-stuck tools now complete without hanging.
Run: python tests/mcp_regression_test.py
"""
import asyncio
import logging
import sys
from pathlib import Path

# Suppress engine log noise so test output is readable
logging.getLogger("HCR").setLevel(logging.ERROR)
logging.getLogger("HCR-MCP").setLevel(logging.ERROR)
logging.getLogger("HCR-MCP-Stdio").setLevel(logging.ERROR)
logging.getLogger("HCRMCPServer").setLevel(logging.ERROR)

sys.path.insert(0, str(Path(__file__).parent.parent))

from product.integrations.mcp_server import HCRMCPResponder


async def run_tests():
    responder = HCRMCPResponder(str(Path(__file__).parent.parent))
    print(f"Engine initialized: {responder.engine is not None}")
    print(f"Persistence initialized: {responder.persistence is not None}")
    print(f"Cross-project initialized: {responder.cross_project is not None}")
    print()

    tools_to_test = [
        ("hcr_get_system_health", {}),
        ("hcr_get_version_history", {"limit": 5}),
        ("hcr_list_shared_states", {}),
        ("hcr_get_shared_state", {"key": "regression_test"}),  # may 404 after cleanup
        ("hcr_get_learned_operators", {}),
        ("hcr_list_sessions", {}),
        ("hcr_capture_full_context", {"include_diffs": False}),
        ("hcr_create_session", {"session_id": "test-session-1", "tag": "regression"}),
        ("hcr_set_session_note", {"session_id": "test-session-1", "note": "regression test note"}),
        ("hcr_merge_session", {"session_id": "test-session-1"}),
        ("hcr_get_current_task", {}),
        ("hcr_get_next_action", {}),
        ("hcr_get_state", {}),
        ("hcr_get_causal_graph", {}),
        ("hcr_get_recent_activity", {"limit": 5}),
        ("hcr_share_state", {"key": "regression_test", "value": {"test": True}}),
        ("hcr_restore_version", {"version_hash": "nonexistent"}),  # expected 404
        ("hcr_record_file_edit", {"filepath": "tests/mcp_regression_test.py", "change_summary": "regression test"}),
        ("hcr_analyze_impact", {"file_path": "src/engine_api.py"}),
        ("hcr_get_recommendations", {}),
        ("hcr_search_history", {"query": "test"}),
    ]

    passed = 0
    failed = 0

    for name, args in tools_to_test:
        try:
            print(f"Testing {name}...", end=" ", flush=True)
            result = await asyncio.wait_for(
                responder._handle_tools_call({"name": name, "arguments": args}),
                timeout=20.0
            )
            is_error = result.get("result", {}).get("isError", False)
            if is_error:
                text = result.get("result", {}).get("content", [{}])[0].get("text", "")
                print(f"ERROR: {text[:80]}")
                failed += 1
            else:
                print("OK")
                passed += 1
        except asyncio.TimeoutError:
            print("TIMEOUT (still stuck)")
            failed += 1
        except Exception as e:
            print(f"EXCEPTION: {e}")
            failed += 1

    print()
    result_line = f"Results: {passed} passed, {failed} failed out of {len(tools_to_test)} tools"
    print(result_line)
    with open("tests/mcp_regression_results.log", "w") as f:
        f.write(result_line + "\n")

    return failed == 0


if __name__ == "__main__":
    ok = asyncio.run(run_tests())
    sys.exit(0 if ok else 1)
