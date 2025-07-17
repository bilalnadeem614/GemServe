import requests

OLLAMA_MODEL_NAME = "gemma3n:e2b"

def ask_gemma(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": OLLAMA_MODEL_NAME, "prompt": prompt, "stream": False}
    )
    return response.json().get("response", "[No response]")