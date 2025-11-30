import requests
import json
import sys

def test_ollama():
    print("Testing Ollama Connectivity...")
    
    url = "http://localhost:11434/api/generate"
    model = "llama3:latest"
    
    payload = {
        "model": model,
        "prompt": "Say hello!",
        "stream": False
    }
    
    try:
        print(f"Connecting to {url} with model '{model}'...")
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("Success! Ollama is responding.")
            print(f"Response: {response.json().get('response')}")
            return True
        else:
            print(f"Failed. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Connection Error: Could not connect to Ollama.")
        print("Make sure Ollama is running (run 'ollama serve' in a terminal).")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    if test_ollama():
        sys.exit(0)
    else:
        sys.exit(1)
