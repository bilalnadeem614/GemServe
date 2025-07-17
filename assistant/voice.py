import queue
import sounddevice as sd
import json
import pyttsx3
from vosk import Model, KaldiRecognizer

q = queue.Queue()
MODEL_PATH = "./models/vosk-model-small-en-us-0.15"

model = Model(MODEL_PATH)

def callback(indata, frames, time, status):
    if status:
        print("⚠️", status)
    q.put(bytes(indata))

def listen_and_transcribe():
    rec = KaldiRecognizer(model, 16000)
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                return result.get("text", "")

def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()