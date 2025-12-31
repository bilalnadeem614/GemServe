# services/llm_service.py
import requests
import json
import time
from utils.config import (
    OLLAMA_BASE_URL, 
    OLLAMA_MODEL, 
    MODEL_CONFIG, 
    DEFAULT_MODE,
    DEFAULT_REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY
)

def ask_ollama(prompt, mode="fast"):
    """
    Send prompt to Ollama and get response with validation and retry logic
    Args:
        prompt: The prompt to send to the model
        mode: "fast" (gemma3:270m) or "thinking" (gemma3n:e2b)
    Returns:
        Response string or error message
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    # Get model config based on mode
    model_config = MODEL_CONFIG.get(mode, {})
    model_name = model_config.get("model", OLLAMA_MODEL)
    timeout = model_config.get("timeout", DEFAULT_REQUEST_TIMEOUT)
    
    data = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }
    
    print(f"Sending prompt to {model_name} (timeout: {timeout}s, mode: {mode})")
    
    # Retry logic
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=data, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            response_text = result.get("response", "").strip()
            
            # Validate response is not empty
            if not response_text:
                error_msg = f"Model returned empty response (attempt {attempt + 1}/{MAX_RETRIES + 1})"
                print(f"⚠️ {error_msg}")
                
                if attempt < MAX_RETRIES:
                    print(f"Retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    return "❌ Error: Model returned no response after multiple attempts. Please try again."
            
            # Validate response length (at least 10 chars to avoid truncation)
            if len(response_text) < 10:
                print(f"⚠️ Response appears truncated (length: {len(response_text)})")
                return f"⚠️ Model response appears incomplete. Please try again.\n\n{response_text}"
            
            print(f"✅ Got valid response from {model_name} ({len(response_text)} chars)")
            return response_text
        
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Cannot connect to Ollama (attempt {attempt + 1}/{MAX_RETRIES + 1})"
            print(f"🔴 {error_msg}")
            
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                return "❌ Error: Cannot connect to Ollama. Make sure Ollama is running on http://localhost:11434"
        
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timed out after {timeout}s (attempt {attempt + 1}/{MAX_RETRIES + 1})"
            print(f"🔴 {error_msg}")
            
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                return f"❌ Error: Model took too long to respond ({timeout}s timeout). Please try again or use Fast mode for quicker responses."
        
        except json.JSONDecodeError as e:
            error_msg = f"Invalid response format from Ollama (attempt {attempt + 1}/{MAX_RETRIES + 1})"
            print(f"🔴 {error_msg}: {str(e)}")
            
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                return "❌ Error: Ollama returned malformed response. Please check if Ollama is working properly."
        
        except Exception as e:
            error_msg = f"Unexpected error (attempt {attempt + 1}/{MAX_RETRIES + 1}): {str(e)}"
            print(f"🔴 {error_msg}")
            
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                return f"❌ Error: {str(e)}"
    
    return "❌ Error: Failed to get response after multiple attempts."