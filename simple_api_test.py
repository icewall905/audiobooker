#!/usr/bin/env python3
"""
Simple test for the Chatterbox Gradio API.
"""

import requests
import json
import time

def test_chatterbox_api():
    """Test the Chatterbox API with a simple request."""
    server_url = "http://10.0.10.23:7860"
    
    print(f"Testing Chatterbox API at {server_url}")
    
    # First, test basic connectivity
    try:
        response = requests.get(server_url, timeout=10)
        print(f"✅ Server accessible (status: {response.status_code})")
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return False
    
    # Test the queue/join endpoint with proper Gradio format
    queue_url = f"{server_url}/queue/join"
    
    # Based on the Gradio config we saw earlier, the generate function expects:
    # [state, text, audio_file, exaggeration, temperature, seed, cfg_weight]
    payload = {
        "data": [
            None,           # state (internal)
            "Hello world. This is a test.",  # text to synthesize
            None,           # audio file (None for default voice)
            0.5,            # exaggeration
            0.8,            # temperature
            0,              # seed (0 for random)
            0.5             # cfg_weight
        ],
        "fn_index": 1,      # Function index (1 for generate)
        "session_hash": "test_session_123"
    }
    
    print(f"\nSending request to: {queue_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(queue_url, json=payload, timeout=30)
        print(f"\nResponse status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Request queued successfully")
            
            # Check if we got an event_id to track progress
            if "event_id" in result:
                event_id = result["event_id"]
                print(f"Event ID: {event_id}")
                
                # Poll for completion (simplified version)
                status_url = f"{server_url}/queue/status"
                print(f"Checking status at: {status_url}")
                
                for i in range(10):  # Check up to 10 times
                    time.sleep(2)
                    try:
                        status_response = requests.get(status_url, timeout=10)
                        print(f"Status check {i+1}: {status_response.status_code}")
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print(f"Status data: {status_data}")
                    except Exception as e:
                        print(f"Status check failed: {e}")
                        
            return True
        else:
            print("❌ Request failed")
            return False
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

def main():
    print("=== Simple Chatterbox API Test ===\n")
    
    success = test_chatterbox_api()
    
    if success:
        print("\n✅ Basic API communication working")
        print("If you didn't get audio output, the API structure might need adjustment")
    else:
        print("\n❌ API communication failed")
        print("Check if the server is running and accessible")
    
    print(f"\n💡 Alternative approach:")
    print(f"Open http://10.0.10.23:7860 in your browser and test manually")

if __name__ == "__main__":
    main()
