# services/llm_service.py
import requests

from utils.config import GEMINI_API_KEY, OLLAMA_BASE_URL, OLLAMA_FAST_MODEL, OLLAMA_THINKING_MODEL

# Backward-compat: some imports expect OLLAMA_MODEL
try:
    from utils.config import OLLAMA_MODEL
except ImportError:
    OLLAMA_MODEL = OLLAMA_FAST_MODEL

_FALLBACK = "I'm not sure how to respond to that. Could you rephrase or ask something else?"


def _extract_gemini_sources(response) -> list[dict]:
    sources = []

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        grounding_metadata = getattr(candidate, "grounding_metadata", None)
        grounding_chunks = getattr(grounding_metadata, "grounding_chunks", None) if grounding_metadata else None
        if not grounding_chunks:
            continue

        for chunk in grounding_chunks:
            web = getattr(chunk, "web", None)
            if not web:
                continue

            title = getattr(web, "title", None) or getattr(web, "site_name", None) or "Source"
            uri = getattr(web, "uri", None) or getattr(web, "url", None)
            if uri:
                sources.append({"title": title, "uri": uri})

    deduped = []
    seen = set()
    for source in sources:
        key = (source["title"], source["uri"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)

    return deduped


def _call_ollama_chat(messages: list, model: str, timeout: int = 60, retries: int = 2) -> str:
    """
    Call Ollama /api/chat with a proper messages array.
    Correctly separates system prompt from conversation so the model
    does NOT re-introduce itself on every reply.

    messages format:
        [{"role": "system",    "content": "..."},
         {"role": "user",      "content": "..."},
         {"role": "assistant", "content": "..."},
         {"role": "user",      "content": "current query"}]
    """
    url  = f"{OLLAMA_BASE_URL}/api/chat"
    data = {"model": model, "messages": messages, "stream": False}

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, json=data, timeout=timeout)
            response.raise_for_status()
            text = response.json().get("message", {}).get("content", "").strip()
            if text:
                return text
            print(f"⚠️ Empty response from {model} (attempt {attempt}/{retries})")
        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to Ollama. Make sure Ollama is running."
        except requests.exceptions.Timeout:
            return "❌ Request timed out. The model might be loading — try again."
        except Exception as e:
            return f"❌ Error: {str(e)}"

    return _FALLBACK


def _call_ollama(prompt: str, model: str, timeout: int = 60, retries: int = 2) -> str:
    """
    Legacy /api/generate caller — kept for backward compatibility.
    Used by ask_ollama() and file intent parsing.
    """
    url  = f"{OLLAMA_BASE_URL}/api/generate"
    data = {"model": model, "prompt": prompt, "stream": False}

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, json=data, timeout=timeout)
            response.raise_for_status()
            text = response.json().get("response", "").strip()
            if text:
                return text
            print(f"⚠️ Empty response from {model} (attempt {attempt}/{retries})")
        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to Ollama. Make sure Ollama is running."
        except requests.exceptions.Timeout:
            return "❌ Request timed out. The model might be loading — try again."
        except Exception as e:
            return f"❌ Error: {str(e)}"

    return _FALLBACK

# def _call_ollama(prompt: str, model: str, timeout: int = 15) -> str:
#     """
#     Internal helper for quick single-shot LLM calls.
#     Used by system_intent_service for intent parsing.
#     """
#     url = f"{OLLAMA_BASE_URL}/api/generate"
#     data = {
#         "model": model,
#         "prompt": prompt,
#         "stream": False
#     }
#     try:
#         response = requests.post(url, json=data, timeout=timeout)
#         response.raise_for_status()
#         result = response.json()
#         return result.get("response", "").strip()
#     except Exception as e:
#         raise Exception(f"Ollama call failed: {str(e)}")

def ask_ollama(prompt: str) -> str:
    """Send a plain prompt using the fast model. Used by file intent parsing."""
    return _call_ollama(prompt, OLLAMA_FAST_MODEL, timeout=30)


def call_gemini_search(user_query: str) -> dict:
    if not GEMINI_API_KEY:
        return {"answer": "❌ Error: GEMINI_API_KEY not found in .env file.", "sources": []}

    try:
        from google import genai
        from google.genai.types import GoogleSearch, Tool
    except Exception:
        return {
            "answer": "❌ Search Error: google-genai is not installed in this Python environment.",
            "sources": [],
        }

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        search_tool = Tool(google_search=GoogleSearch())

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_query,
            config={"tools": [search_tool]},
        )

        return {
            "answer": getattr(response, "text", "") or "",
            "sources": _extract_gemini_sources(response),
        }
    except Exception as e:
        return {"answer": f"❌ Search Error: {str(e)}", "sources": []}


def get_chat_response(session_id, user_query: str, mode: str = "fast") -> str:
    """Lightweight wrapper — used only if chat_service is not available."""
    model   = OLLAMA_FAST_MODEL if mode == "fast" else OLLAMA_THINKING_MODEL
    timeout = 60 if mode == "fast" else 180
    return _call_ollama(user_query, model, timeout)