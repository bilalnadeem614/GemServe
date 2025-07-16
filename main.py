import requests
import pyttsx3
from vosk import Model, KaldiRecognizer
import sounddevice as sd
import json
import queue

# === CONFIG ===
VOSK_MODEL_PATH = "models/vosk-model-small-en-us-0.15"
OLLAMA_MODEL_NAME = "gemma3n:e2b"

# === VOICE INPUT SETUP ===
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print("⚠️", status)
    q.put(bytes(indata))

def listen_and_transcribe():
    print("🎤 Speak something...")
    model = Model(VOSK_MODEL_PATH)
    rec = KaldiRecognizer(model, 16000)

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        print("Listening (say something short)...")
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                return result.get("text", "")
                
# === OLLAMA CALL ===
def ask_gemma(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": OLLAMA_MODEL_NAME, "prompt": prompt, "stream": False}
    )
    return response.json().get("response", "[No response]")

# === TTS ===
def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# === MAIN ===
if __name__ == "__main__":
    try:
        prompt = listen_and_transcribe()
        print("📝 You said:", prompt)

        response = ask_gemma(prompt)
        print("🤖 Gemma3n:", response)

        speak(response)

    except Exception as e:
        print("❌ Error:", e)
