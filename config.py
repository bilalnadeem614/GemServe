import os
import requests
# Get the absolute path of the project's root directory
# This makes it easier to create absolute paths from relative ones
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Voice Model Configuration ---
# Path to the Vosk model directory.
# We use os.path.join to create a system-agnostic path (works on Windows, Mac, Linux)
VOSK_MODEL_PATH = os.path.join(BASE_DIR, "models", "vosk-model-small-en-us-0.15")

# --- Assistant Configuration ---
ASSISTANT_NAME = "GemServe"


OLLAMA_MODEL_NAME = "gemma3n:e2b"

def ask_gemma(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": OLLAMA_MODEL_NAME, "prompt": prompt, "stream": False}
    )
    return response.json().get("response", "[No response]")

# --- Assistant Configuration ---
# ASSISTANT_NAME = "GemServe"

# # LLM Model
# OLLAMA_MODEL_NAME = "gemma3n:e2b"
# OLLAMA_API_URL = "http://localhost:11434/api/generate"

# # Paths
# VOSK_MODEL_PATH = "models/vosk-model-small-en-us-0.15"

# import requests

# def ask_gemma(prompt):
#     try:
#         response = requests.post(
#             OLLAMA_API_URL,
#             json={"model": OLLAMA_MODEL_NAME, "prompt": prompt, "stream": False},
#             timeout=60
#         )
#         return response.json().get("response", "[No response]")
#     except Exception as e:
#         return f"[Error calling LLM] {e}"
