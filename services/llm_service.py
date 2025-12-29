# services/llm_service.py
import requests
import json
from utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL, MODEL_CONFIG, DEFAULT_MODE

def ask_ollama(prompt, mode="fast"):
    """
    Send prompt to Ollama and get response
    Args:
        prompt: The prompt to send to the model
        mode: "fast" (gemma3:270m) or "thinking" (gemma3n:e2b)
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    # Get model name based on mode
    model_name = MODEL_CONFIG.get(mode, {}).get("model", OLLAMA_MODEL)
    
    data = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "Sorry, I couldn't generate a response.")
    
    except requests.exceptions.ConnectionError:
        return "❌ Error: Cannot connect to Ollama. Make sure Ollama is running."
    except requests.exceptions.Timeout:
        return "❌ Error: Request timed out. The model might be processing."
    except Exception as e:
        return f"❌ Error: {str(e)}"