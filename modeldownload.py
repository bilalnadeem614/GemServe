from faster_whisper import WhisperModel
import os

MODELS_DIR = "models/whisper"
os.makedirs(MODELS_DIR, exist_ok=True)

print("\nDownloading base model (~74MB)...")
WhisperModel("base", device="cpu", compute_type="int8", download_root=MODELS_DIR)
print("✅ base model ready")