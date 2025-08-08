import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from assistant.voice import listen_and_transcribe, speak
from assistant.llm import ask_gemma
from assistant import core
print("✅ Import success!")