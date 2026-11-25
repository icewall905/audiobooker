#!/usr/bin/env python3
"""
Test SSE streaming with the exact Gradio approach.
"""

import requests
import json
import time
import uuid

SERVER_URL = "http://10.0.10.23:7860"

def test_sse_streaming():
    """Test proper SSE streaming approach."""
    
    # Generate a session hash like Gradio does
    session_hash = str(uuid.uuid4()).replace('-', '')[:16]
    print(f"Generated session_hash: {session_hash}")
    
    # Step 1: Join the queue with the session hash
    join_data = {
        "data": [
            None,  # State object
            "Hello world test",  # Input text
            None,  # Voice prompt file
            0.5,   # Exaggeration parameter
            0.8,   # Temperature parameter
            0,     # Random seed
            0.5    # CFG weight parameter
        ],
        "event_data": None,
        "fn_index": 1,  # Use the correct fn_index from config (dependency id 1)
        "trigger_id": None,
        "session_hash": session_hash
    }
    
    print("=== Step 1: Joining Queue ===")
    join_url = f"{SERVER_URL}/queue/join"
    
    try:
        join_response = requests.post(join_url, json=join_data, timeout=30)
        print(f"Queue join response status: {join_response.status_code}")
        
        if join_response.status_code == 200:
            join_result = join_response.json()
            print(f"Queue join result: {json.dumps(join_result, indent=2)}")
        else:
            print(f"Queue join failed: {join_response.text}")
            
    except Exception as e:
        print(f"Queue join error: {e}")
    
    # Step 2: Try SSE streaming with the session hash
    print(f"\n=== Step 2: SSE Streaming ===")
    sse_url = f"{SERVER_URL}/queue/data"
    
    try:
        sse_response = requests.get(
            sse_url, 
            params={"session_hash": session_hash},
            stream=True, 
            timeout=60,
            headers={"Accept": "text/event-stream"}
        )
        
        print(f"SSE response status: {sse_response.status_code}")
        print(f"SSE response headers: {dict(sse_response.headers)}")
        
        if sse_response.status_code == 200:
            print("Processing SSE stream...")
            
            for line_num, line in enumerate(sse_response.iter_lines(decode_unicode=True)):
                if line_num > 50:  # Limit output
                    print("... (truncated after 50 lines)")
                    break
                    
                print(f"Line {line_num}: {line}")
                
                if line and line.startswith('data: '):
                    data_str = line[6:]
                    if data_str.strip() in ['[DONE]', 'null', '']:
                        continue
                    
                    try:
                        data = json.loads(data_str)
                        print(f"  Parsed data: {json.dumps(data, indent=4)}")
                        
                        if data.get('msg') == 'process_completed':
                            print("🎉 Process completed!")
                            if 'output' in data:
                                print(f"Output data: {data['output']}")
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"  JSON decode error: {e}")
                        
        else:
            print(f"SSE failed: {sse_response.text}")
            
    except Exception as e:
        print(f"SSE error: {e}")

if __name__ == "__main__":
    test_sse_streaming()
