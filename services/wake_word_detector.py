"""Wake word detection utilities backed by Faster Whisper."""

from __future__ import annotations

import logging
import queue
import threading
from datetime import datetime
from typing import Any

import numpy as np

from PySide6.QtCore import QObject, QThread, Signal, Slot

from services.model_manager import ModelManager


logger = logging.getLogger(__name__)


class _WakeWordProcessor(QObject):
    """Qt worker that drives the detector processing loop."""

    finished = Signal(bool)

    def __init__(self, detector: "WakeWordDetector") -> None:
        """Store the detector instance used by the worker."""
        super().__init__()
        self._detector = detector

    @Slot()
    def run(self) -> None:
        """Run the detector loop in a QThread context."""
        logger.info("Wake word worker run() entered.")
        if not self._detector._listening:
            logger.debug("Wake word worker started while detector was not listening.")
            self.finished.emit(False)
            return

        try:
            logger.info("Wake word worker entering process_audio_loop().")
            detected = self._detector.process_audio_loop()
            self.finished.emit(detected)
        except Exception:
            logger.exception("Wake word worker crashed.")
            self.finished.emit(False)


class WakeWordDetector(QObject):
    """Detect wake words from transcribed audio."""

    wake_word_detected = Signal(str)

    def __init__(
        self,
        model_manager: ModelManager,
        debug_mode: bool = False,
    ) -> None:
        """Initialize the detector and load a Whisper tiny model.

        Args:
            model_manager: Shared model manager used to load the Whisper tiny model.
            debug_mode: When True, emit verbose diagnostic logging.
        """
        super().__init__()
        self.model_manager = model_manager
        self.debug_mode = debug_mode
        self.noise_threshold = 0.01
        self.audio_queue: queue.Queue[Any] = queue.Queue(maxsize=5)
        self._listening = False
        self._stream: Any | None = None
        self._thread_lock = threading.Lock()
        self._worker_thread: QThread | None = None
        self._worker: _WakeWordProcessor | None = None

        self._log_info("WakeWordDetector initialized.")
        self._log_debug(
            "Detector settings noise_threshold=%s debug_mode=%s",
            self.noise_threshold,
            self.debug_mode,
        )

    def _timestamp(self) -> str:
        """Return an ISO 8601 timestamp for logging."""
        return datetime.now().isoformat(timespec="milliseconds")

    def _log_debug(self, message: str, *args: Any) -> None:
        """Emit verbose debug logging only when debug mode is enabled."""
        if self.debug_mode:
            logger.debug(message, *args)

    def _log_info(self, message: str, *args: Any) -> None:
        """Emit informational logs with a consistent wake-word prefix."""
        logger.info("[WakeWordDetector] " + message, *args)

    def _log_error(self, message: str, *args: Any) -> None:
        """Emit error logs with a consistent wake-word prefix."""
        logger.error("[WakeWordDetector] " + message, *args)

    def start_listening(self) -> None:
        """Start continuously recording 1-second audio chunks from the microphone.

        The captured chunks are placed into :attr:`audio_queue` for later
        transcription or wake-word processing.

        Raises:
            RuntimeError: If the microphone cannot be accessed or listening
                cannot be started.
        """
        if self._listening:
            self._log_debug("start_listening() called while already listening.")
            return

        self._log_info("start_listening() requested at %s.", self._timestamp())

        try:
            import sounddevice as sd
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError("sounddevice is required for microphone access.") from exc

        samplerate = 16_000
        chunk_size = samplerate

        def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            """Store each recorded chunk for later processing."""
            captured_at = self._timestamp()
            if status:
                self._log_debug("Microphone status at %s: %s", captured_at, status)
                self.audio_queue.put({"status": str(status)})
            if self.audio_queue.full():
                try:
                    dropped = self.audio_queue.get_nowait()
                    dropped_timestamp = dropped.get("timestamp") if isinstance(dropped, dict) else None
                    self._log_debug(
                        "Dropping stale audio chunk before enqueueing new one%s.",
                        f" captured at {dropped_timestamp}" if dropped_timestamp else "",
                    )
                except queue.Empty:
                    pass
            self.audio_queue.put({"audio": indata.copy(), "timestamp": captured_at})
            self._log_debug(
                "Recorded audio chunk at %s (frames=%s, shape=%s)",
                captured_at,
                frames,
                getattr(indata, "shape", None),
            )

        try:
            self._log_debug("Opening microphone InputStream at %s.", self._timestamp())
            self._stream = sd.InputStream(
                samplerate=samplerate,
                channels=1,
                dtype="float32",
                blocksize=chunk_size,
                callback=callback,
            )
            self._stream.start()
            self._listening = True
            self._log_info("Listening started at %s.", self._timestamp())
        except Exception as exc:
            self._stream = None
            self._listening = False
            message = str(exc).strip() or "Unable to access the microphone."
            self._log_error("Failed to start microphone stream at %s: %s", self._timestamp(), message)
            logger.exception("Failed to start microphone stream.")
            raise RuntimeError(f"Microphone access error: {message}") from exc

    def start_background_thread(self) -> QThread:
        """Start the wake-word processing loop safely in a QThread.

        Returns:
            The running QThread instance.

        Raises:
            RuntimeError: If the microphone cannot be started or the worker
                thread cannot be created.
        """
        with self._thread_lock:
            self._log_info("start_background_thread() requested at %s.", self._timestamp())
            if self._worker_thread is not None and self._worker_thread.isRunning():
                self._log_debug("Wake word background thread already running.")
                return self._worker_thread

            if not self._listening:
                self._log_debug("Detector not listening yet; starting microphone stream first.")
                self.start_listening()

            self._worker_thread = QThread(self)
            self._worker = _WakeWordProcessor(self)
            self._worker.moveToThread(self._worker_thread)
            self._worker_thread.started.connect(self._worker.run)
            self._worker.finished.connect(self._worker_thread.quit)
            self._worker.finished.connect(self._worker.deleteLater)
            self._worker_thread.finished.connect(self._worker_thread.deleteLater)
            self._worker_thread.finished.connect(self._on_worker_thread_finished)
            self._log_debug("Starting wake word QThread now.")
            self._worker_thread.start()
            self._log_debug("Wake word background thread started at %s.", self._timestamp())
            return self._worker_thread

    def stop_listening(self) -> None:
        """Stop microphone capture started by :meth:`start_listening`."""
        self._listening = False
        if self._stream is not None:
            try:
                self._stream.stop()
            finally:
                self._stream.close()
                self._stream = None
                self._log_info("Listening stopped at %s.", self._timestamp())

    def stop_detector_gracefully(self) -> None:
        """Stop the detector, thread, and microphone stream cleanly."""
        with self._thread_lock:
            self._log_debug("Stopping wake word detector gracefully at %s.", self._timestamp())
            self.stop_listening()

            if self._worker_thread is not None:
                self._worker_thread.quit()
                if not self._worker_thread.wait(3000):
                    logger.warning("Wake word thread did not stop within timeout.")
                self._worker_thread = None
                self._worker = None

    @Slot()
    def _on_worker_thread_finished(self) -> None:
        """Clean up worker state after the QThread exits."""
        self._log_debug("Wake word worker finished at %s.", self._timestamp())
        self._worker = None
        self._worker_thread = None

    def process_audio_loop(self) -> bool:
        """Process queued audio chunks until a wake word is detected.

        This method is intended to be executed in a background thread. It reads
        audio chunks from :attr:`audio_queue`, transcribes them with the tiny
        Whisper model, and checks each transcription with :meth:`is_wake_word`.

        Returns:
            True as soon as a wake word is detected, otherwise False when the
            listening session ends without a match.
        """
        self._log_info("process_audio_loop() entered at %s.", self._timestamp())
        self._log_debug(
            "Initial loop state listening=%s queue_size=%s",
            self._listening,
            self.audio_queue.qsize(),
        )
        self._log_debug("Waiting for audio chunks from microphone queue.")

        while self._listening or not self.audio_queue.empty():
            try:
                queued_item = self.audio_queue.get(timeout=0.2)
            except queue.Empty:
                self._log_debug("Audio queue empty, still listening=%s.", self._listening)
                continue

            if isinstance(queued_item, dict) and "status" in queued_item and "audio" not in queued_item:
                self._log_debug("Audio stream status event: %s", queued_item["status"])
                continue

            audio_chunk = queued_item.get("audio") if isinstance(queued_item, dict) else queued_item
            chunk_timestamp = queued_item.get("timestamp") if isinstance(queued_item, dict) else self._timestamp()

            self._log_debug("Processing chunk captured at %s.", chunk_timestamp)

            if not self.apply_noise_gate(audio_chunk):
                self._log_debug("Rejected low-noise chunk captured at %s.", chunk_timestamp)
                continue

            self._log_info("Chunk accepted for transcription at %s.", chunk_timestamp)

            self._log_debug("Transcribing chunk captured at %s.", chunk_timestamp)

            try:
                transcription = self.transcribe_audio(audio_chunk)
            except Exception:
                self._log_error("Failed to transcribe chunk captured at %s.", chunk_timestamp)
                logger.exception("Failed to transcribe queued audio chunk.")
                continue

            cleaned_transcription = transcription.strip()

            if not cleaned_transcription:
                self._log_debug("Rejected empty transcription for chunk at %s.", chunk_timestamp)
                continue

            if len(cleaned_transcription) < 2:
                self._log_debug(
                    "Rejected too-short transcription for chunk at %s: %r",
                    chunk_timestamp,
                    cleaned_transcription,
                )
                continue

            self._log_info(
                "Transcription complete at %s: %s",
                self._timestamp(),
                cleaned_transcription,
            )
            self._log_debug(
                "Chunk captured at %s transcribed to: %r",
                chunk_timestamp,
                cleaned_transcription,
            )

            if self.is_wake_word(cleaned_transcription):
                self._log_info(
                    "Wake word detected at %s: %s",
                    self._timestamp(),
                    cleaned_transcription,
                )
                self.wake_word_detected.emit(cleaned_transcription)
                return True

        self._log_debug("Wake word processing loop ended without detection at %s.", self._timestamp())
        return False

    def apply_noise_gate(self, audio_chunk: Any) -> bool:
        """Return True only when the chunk's RMS energy exceeds the threshold."""
        audio_array = np.asarray(audio_chunk, dtype=np.float32).flatten()
        if audio_array.size == 0:
            self._log_debug("Noise gate rejected empty audio chunk.")
            return False

        rms = float(np.sqrt(np.mean(np.square(audio_array))))
        self._log_debug("Audio chunk RMS=%s threshold=%s", rms, self.noise_threshold)
        return rms > self.noise_threshold

    def transcribe_audio(self, audio_data: Any) -> str:
        """Transcribe provided audio into text.

        Args:
            audio_data: Audio input accepted by Faster Whisper (e.g., file path,
                bytes-like stream, or numpy array).

        Returns:
            The transcribed text.
        """

        try:
            model = self.model_manager.get_tiny_model()
        except Exception as exc:
            self._log_error("Model loading failed at %s: %s", self._timestamp(), exc)
            logger.exception("Tiny model loading failed.")
            raise

        normalized_audio = np.asarray(audio_data, dtype=np.float32).flatten()
        initial_prompt = "hey hello hi"
        segments, _ = model.transcribe(
            normalized_audio,
            language="en",
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
            initial_prompt=initial_prompt,
        )
        transcription = " ".join(segment.text for segment in segments).strip()
        self._log_debug("Model transcription finished at %s: %r", self._timestamp(), transcription)
        return transcription

    def is_wake_word(self, text: str) -> bool:
        """Check if the transcribed text contains a wake word.

        Args:
            text: Transcribed text to inspect.

        Returns:
            True when the text contains "hi", "hey" or "hello" (case-insensitive),
            otherwise False.
        """
        lowered = text.lower()
        return "hi" in lowered or "hey" in lowered or "hello" in lowered
