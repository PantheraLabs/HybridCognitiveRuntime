import asyncio
import json
from product.integrations.mcp_server import HCRMCPResponder

async def test_all_tools():
    r = HCRMCPResponder('.')
    results = {}
    
    tests = [
        ('hcr_get_state', {}),
        ('hcr_get_causal_graph', {}),
        ('hcr_get_recent_activity', {}),
        ('hcr_get_current_task', {}),
        ('hcr_get_next_action', {}),
        ('hcr_list_shared_states', {}),
        ('hcr_get_shared_state', {'key': 'test'}),
        ('hcr_share_state', {'key': 'demo', 'value': 'test_val'}),
        ('hcr_get_version_history', {}),
        ('hcr_restore_version', {'version_hash': 'dummy'}),
        ('hcr_get_learned_operators', {}),
        ('hcr_get_system_health', {}),
        ('hcr_list_sessions', {}),
        ('hcr_create_session', {'session_id': 'test-pane', 'tag': 'Test Session'}),
        ('hcr_set_session_note', {'session_id': 'test-pane', 'note': 'Testing multi-window'}),
        ('hcr_list_sessions', {}),
        ('hcr_merge_session', {'session_id': 'test-pane'}),
    ]
    
    for name, args in tests:
        handler_name = '_tool_' + name.replace('hcr_', '')
        handler = getattr(r, handler_name, None)
        if not handler:
            results[name] = {'ok': False, 'error': 'No handler found'}
            continue
        try:
            result = await handler(args)
            has_content = isinstance(result, dict) and 'content' in result
            results[name] = {
                'ok': True, 
                'has_content': has_content, 
                'keys': list(result.keys()) if isinstance(result, dict) else []
            }
        except Exception as e:
            results[name] = {'ok': False, 'error': str(e)[:80]}
    
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    asyncio.run(test_all_tools())
