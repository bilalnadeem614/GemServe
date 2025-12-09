# services/llm_service.py
import requests
import json
from utils.config import OLLAMA_BASE_URL, OLLAMA_MODEL

def ask_ollama(prompt):
    """
    Send prompt to Ollama and get response
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    data = {
        "model": OLLAMA_MODEL,
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