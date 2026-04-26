#!/usr/bin/env python3
"""Test HCR MCP tools directly"""

import sys
import json
import subprocess

def call_tool(name, args=None):
    """Call MCP tool via server"""
    proc = subprocess.Popen(
        [sys.executable, 'mcp_server_stdio.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Initialize
    init = {'jsonrpc': '2.0', 'id': 0, 'method': 'initialize', 'params': {}}
    proc.stdin.write(json.dumps(init) + '\n')
    proc.stdin.flush()
    proc.stdout.readline()  # Skip init response
    
    # Call tool
    call = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {'name': name, 'arguments': args or {}}
    }
    proc.stdin.write(json.dumps(call) + '\n')
    proc.stdin.flush()
    
    # Get response
    resp = json.loads(proc.stdout.readline())
    proc.terminate()
    
    return resp


if __name__ == '__main__':
    print("="*60)
    print("HCR MCP TOOLS TEST")
    print("="*60)
    
    # Test 1: check_hcr_status
    print("\n1. check_hcr_status()")
    print("-"*40)
    r = call_tool('check_hcr_status')
    if 'result' in r:
        print(r['result']['content'][0]['text'])
    else:
        print("Error:", r)
    
    # Test 2: get_hcr_context
    print("\n2. get_hcr_context()")
    print("-"*40)
    r = call_tool('get_hcr_context')
    if 'result' in r:
        print(r['result']['content'][0]['text'])
    else:
        print("Error:", r)
    
    # Test 3: resume_session
    print("\n3. resume_session(gap_minutes=45)")
    print("-"*40)
    r = call_tool('resume_session', {'gap_minutes': 45})
    if 'result' in r:
        print(r['result']['content'][0]['text'])
    else:
        print("Error:", r)
    
    # Test 4: update_hcr_state
    print("\n4. update_hcr_state(event_type='file_edit')")
    print("-"*40)
    r = call_tool('update_hcr_state', {'event_type': 'file_edit', 'file_path': 'test.py'})
    if 'result' in r:
        print(r['result']['content'][0]['text'])
    else:
        print("Error:", r)
    
    print("\n" + "="*60)
    print("ALL TOOLS TESTED")
    print("="*60)
