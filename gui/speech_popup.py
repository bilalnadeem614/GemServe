"""
GemServe - Speech to Text Popup Dialog
- No buttons, no waveform bars — fully automatic flow
- Opens → starts listening → detects 3s silence → transcribes → sends to chat → closes
Requires: PySide6, faster-whisper, sounddevice, numpy
Install: pip install PySide6 faster-whisper sounddevice numpy
"""

import sys
import threading
import queue
import math
import time
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QFrame, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QObject, QThread, QRect, Slot
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient,
    QPainterPath, QRadialGradient, QCursor
)

from services.model_manager import ModelManager

C_GRAD_TOP = QColor("#7C3AED")
C_GRAD_BOT = QColor("#9D5CF6")

SILENCE_SECONDS    = 2.0
SILENCE_RMS_THRESH = 0.01


# ─────────────────────────────────────────────
#  Animated mic + pulse widget  (NO bars)
# ─────────────────────────────────────────────
class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 160)
        self._phase        = 0.0
        self._active       = False
        self._pulse_radius = 0.0
        self._pulse_dir    = 1

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def set_active(self, active: bool):
        self._active = active

    def _tick(self):
        self._phase += 0.08
        if self._active:
            self._pulse_radius += 0.8 * self._pulse_dir
            if self._pulse_radius > 18 or self._pulse_radius < 0:
                self._pulse_dir *= -1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h   = self.width(), self.height()
        cx, cy = w / 2, h / 2 -15

        p.fillRect(self.rect(), Qt.transparent)

        # ── pulse rings (active only) ────────
        if self._active:
            for ring in range(3):
                r     = 38 + ring * 18 + self._pulse_radius
                alpha = max(0, 80 - ring * 22 - int(self._pulse_radius * 2))
                p.setPen(QPen(QColor(124, 58, 237, alpha), 2))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        # ── mic circle glow ──────────────────
        mic_r = 32
        if self._active:
            grad = QRadialGradient(cx, cy, mic_r + 14)
            grad.setColorAt(0, QColor(124, 58, 237, 70))
            grad.setColorAt(1, QColor(124, 58, 237, 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(cx - mic_r - 14), int(cy - mic_r - 14),
                          int((mic_r + 14) * 2), int((mic_r + 14) * 2))

        # ── mic circle fill ──────────────────
        grad2 = QLinearGradient(cx - mic_r, cy - mic_r, cx + mic_r, cy + mic_r)
        grad2.setColorAt(0, C_GRAD_TOP)
        grad2.setColorAt(1, C_GRAD_BOT)
        p.setBrush(QBrush(grad2))
        p.setPen(Qt.NoPen)
        p.drawEllipse(int(cx - mic_r), int(cy - mic_r), mic_r * 2, mic_r * 2)

        # mic icon
        p.setPen(QPen(QColor(255, 255, 255, 230), 2.5,
                      Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        body_w, body_h = 11, 16
        bx = cx - body_w / 2
        by = cy - body_h / 2 - 6
        path = QPainterPath()
        path.addRoundedRect(bx, by, body_w, body_h, 5.5, 5.5)
        p.drawPath(path)
        arc_r = 15
        p.drawArc(int(cx - arc_r), int(cy - arc_r / 2),
                  int(arc_r * 2), int(arc_r), 0, -180 * 16)
        p.drawLine(int(cx), int(cy + arc_r / 2),
                   int(cx), int(cy + arc_r / 2 + 5))
        p.drawLine(int(cx - 5), int(cy + arc_r / 2 + 5),
                   int(cx + 5), int(cy + arc_r / 2 + 5))

        p.end()


# ─────────────────────────────────────────────
#  Silence countdown ring widget
# ─────────────────────────────────────────────
class SilenceRingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self._progress = 0.0
        self._visible  = False

    def set_progress(self, value: float, visible: bool):
        self._progress = max(0.0, min(1.0, value))
        self._visible  = visible
        self.update()

    def paintEvent(self, event):
        if not self._visible:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy, r = 30, 30, 24
        p.setPen(QPen(QColor(221, 214, 254), 5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        span = int(-self._progress * 360 * 16)
        p.setPen(QPen(QColor("#7C3AED"), 5, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(cx - r, cy - r, r * 2, r * 2, 90 * 16, span)
        secs_left = int(SILENCE_SECONDS * (1 - self._progress)) + 1
        p.setPen(QColor("#7C3AED"))
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.drawText(self.rect(), Qt.AlignCenter, str(secs_left))
        p.end()


# ─────────────────────────────────────────────
#  Worker: record + silence detection + whisper
# ─────────────────────────────────────────────
class TranscribeWorker(QObject):
    transcription_done = Signal(str)
    level_update       = Signal(list)
    status_update      = Signal(str)
    silence_progress   = Signal(float)
    silence_ended      = Signal()
    error_occurred     = Signal(str)

    def __init__(
        self,
        model_manager: ModelManager,
        model_dir: str = "models/whisper",
        triggered_by_wake_word: bool = False,
    ):
        super().__init__()
        self._running = False
        self._model   = None
        self._model_manager = model_manager
        self._triggered_by_wake_word = triggered_by_wake_word
        self._model_dir = model_dir

    def load_model(self):
        try:
            self.status_update.emit("Loading model…")
            if self._triggered_by_wake_word:
                try:
                    self._model = self._model_manager.get_base_model(self._model_dir)
                except MemoryError:
                    self.status_update.emit("Optimizing memory…")
                    self._model = self._model_manager.switch_model(
                        True,
                        base_download_root=self._model_dir,
                    )
            else:
                self._model = self._model_manager.get_base_model(self._model_dir)
            self.status_update.emit("Listening…")
        except Exception as e:
            self.error_occurred.emit(f"Model error: {e}")

    def start_recording(self):
        self._running = True
        threading.Thread(target=self._record_and_transcribe, daemon=True).start()

    def stop_recording(self):
        self._running = False

    def _record_and_transcribe(self):
        import sounddevice as sd
        try:
            samplerate    = 16000
            chunk_size    = 1024
            audio_q       = queue.Queue()
            all_audio     = []
            silence_start = None

            self.status_update.emit("Listening…")

            def callback(indata, frames, time_info, status):
                audio_q.put(indata.copy())

            with sd.InputStream(samplerate=samplerate, channels=1,
                                dtype="float32", blocksize=chunk_size,
                                callback=callback):
                while self._running:
                    try:
                        chunk = audio_q.get(timeout=0.1)
                        all_audio.append(chunk)

                        rms  = float(np.sqrt(np.mean(chunk ** 2)))
                        now  = time.time()

                        if rms < SILENCE_RMS_THRESH:
                            if silence_start is None:
                                silence_start = now
                            elapsed  = now - silence_start
                            progress = elapsed / SILENCE_SECONDS
                            self.silence_progress.emit(min(progress, 1.0))
                            if elapsed >= SILENCE_SECONDS:
                                total_dur = len(all_audio) * chunk_size / samplerate
                                if total_dur > 1.0:
                                    self._running = False
                        else:
                            if silence_start is not None:
                                self.silence_progress.emit(0.0)
                            silence_start = None

                    except queue.Empty:
                        pass

            self.silence_ended.emit()

            if not all_audio:
                self.status_update.emit("No audio captured.")
                return

            self.status_update.emit("Transcribing…")
            audio_np = np.concatenate(all_audio, axis=0).flatten()

            if self._model is None:
                self.error_occurred.emit("Model not loaded.")
                return

            # Provide an initial prompt to bias Whisper toward expected vocabulary
            initial_prompt = (
                "open, close, delete, create, search, remind, add task, file, "
                "move file, rename file, copy, paste, download, upload, screenshot, "
                "open browser, new tab, close tab, switch window, minimize, maximize, "
                "settings, preferences, system, terminal, command prompt, calculator, "
                "play music, stop music, pause, resume, weather, time, schedule, "
                "notifications, report, notes, desktop, document, folder, email, calendar, "
                "Visual Studio Code, vscode, Muhammad, Bilal, Umair, Talha, Zaid, Ali, Rana"
            )

            segments, _ = self._model.transcribe(
                audio_np,
                language="en",
                initial_prompt=initial_prompt,
            )
            text = " ".join([seg.text for seg in segments]).strip()
            self.transcription_done.emit(text or "")
            self.status_update.emit("Done ✓")

        except Exception as e:
            self.error_occurred.emit(str(e))


# ─────────────────────────────────────────────
#  Main popup  —  NO buttons, NO bars
# ─────────────────────────────────────────────
class SpeechPopup(QDialog):
    text_ready = Signal(str)

    def __init__(
        self,
        parent=None,
        model_manager: object = None,
        whisper_model_dir: str = None,
        triggered_by_wake_word: bool = False,
        wake_word_detector: object = None,
    ):
        super().__init__(parent)
        self._recording    = False
        self._model_loaded = False
        self._triggered_by_wake_word = triggered_by_wake_word
        self._model_manager = model_manager or ModelManager()
        self._whisper_model_dir = whisper_model_dir or "models/whisper"

        self._worker_thread = QThread(self)
        self._worker        = TranscribeWorker(
            self._model_manager,
            self._whisper_model_dir,
            self._triggered_by_wake_word,
        )
        self._worker.moveToThread(self._worker_thread)

        self._setup_ui()
        self._connect_signals()
        if wake_word_detector is not None and hasattr(wake_word_detector, "wake_word_detected"):
            wake_word_detector.wake_word_detected.connect(self.accept_wake_word_trigger)
        self._worker_thread.started.connect(self._worker.load_model)
        self._worker_thread.start()

    # ── UI ──────────────────────────────────
    def _setup_ui(self):
        self.setWindowTitle("Voice Input")
        self.setFixedSize(400, 380)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)

        card = QFrame(self)
        card.setObjectName("card")
        card.setStyleSheet("QFrame#card { background: #F5F3FF; border-radius: 18px; }")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(100, 50, 200, 90))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        card_layout.addWidget(self._make_header())

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 18, 20, 22)
        body_layout.setSpacing(14)

        # mic + pulse widget
        wave_wrapper = QWidget()
        wave_wrapper.setStyleSheet("background: white; border-radius: 14px;")
        ww_shadow = QGraphicsDropShadowEffect()
        ww_shadow.setBlurRadius(16)
        ww_shadow.setColor(QColor(124, 58, 237, 30))
        ww_shadow.setOffset(0, 3)
        wave_wrapper.setGraphicsEffect(ww_shadow)
        ww_layout = QVBoxLayout(wave_wrapper)
        ww_layout.setContentsMargins(0, 12, 0, 12)
        ww_layout.setAlignment(Qt.AlignCenter)
        self._waveform = WaveformWidget()
        ww_layout.addWidget(self._waveform, alignment=Qt.AlignCenter)
        body_layout.addWidget(wave_wrapper)

        # status row
        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        self._status_label = QLabel("Initialising…")
        self._status_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._status_label.setFont(QFont("Segoe UI", 10))
        self._status_label.setStyleSheet("color: #7C3AED; background: transparent;")
        status_row.addWidget(self._status_label, stretch=1)
        self._silence_ring = SilenceRingWidget()
        status_row.addWidget(self._silence_ring)
        body_layout.addLayout(status_row)

        # transcription text box (read-only)
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("Your speech will appear here…")
        self._text_edit.setFont(QFont("Segoe UI", 10))
        self._text_edit.setReadOnly(True)
        self._text_edit.setMinimumHeight(80)
        self._text_edit.setMaximumHeight(90)
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 2px solid #DDD6FE;
                border-radius: 12px;
                padding: 10px 12px;
                color: #1E1B4B;
            }
        """)
        body_layout.addWidget(self._text_edit)

        card_layout.addWidget(body)

    def _make_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            background: transparent;
            border-top-left-radius: 18px;
            border-top-right-radius: 18px;
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 14, 0)

        title = QLabel("Voice Input")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: blue; background: transparent;")
        layout.addWidget(title)
        layout.addStretch()

        close_btn = QLabel("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setAlignment(Qt.AlignCenter)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet("""
            QLabel {
                background: rgba(255,255,255,0.22);
                color: white; border-radius: 15px; font-size: 13px;
            }
            QLabel:hover { background: rgba(255,255,255,0.38); }
        """)
        close_btn.mousePressEvent = lambda e: self._on_close()
        layout.addWidget(close_btn)
        return header

    # ── Signals ─────────────────────────────
    def _connect_signals(self):
        self._worker.transcription_done.connect(self._on_transcription)
        self._worker.level_update.connect(self._on_levels)
        self._worker.status_update.connect(self._on_status)
        self._worker.silence_progress.connect(self._on_silence_progress)
        self._worker.silence_ended.connect(self._on_silence_ended)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.status_update.connect(self._auto_start_on_ready)

    # ── Slots ────────────────────────────────
    def _auto_start_on_ready(self, msg: str):
        if msg == "Listening…" and not self._recording and not self._model_loaded:
            self._model_loaded = True
            if self._triggered_by_wake_word:
                self._status_label.setText("Wake word detected...")
            self._start_recording()

    @Slot(str)
    def accept_wake_word_trigger(self, text: str = ""):
        """Accept a wake-word trigger and begin recording immediately.

        Args:
            text: The detected wake-word transcription, if provided by the
                detector.
        """
        self._triggered_by_wake_word = True
        self._status_label.setText("Wake word detected...")

        if self._recording:
            return

        QTimer.singleShot(0, self._start_recording)

    def _start_recording(self):
        if self._recording:
            return
        self._recording = True
        self._waveform.set_active(True)
        self._worker.start_recording()

    def _on_transcription(self, text: str):
        if not text:
            QTimer.singleShot(600, self.accept)
            return

        self._text_edit.setPlainText(text)

        if self._triggered_by_wake_word:
            parent = self.parentWidget()
            if parent is not None and hasattr(parent, "input") and hasattr(parent, "on_send"):
                parent.input.setPlainText(text)
                # Mark the parent so it knows this input came from voice (wake-word path)
                try:
                    setattr(parent, "_last_input_was_voice", True)
                except Exception:
                    pass
                parent.on_send()
            else:
                self.text_ready.emit(text)
            QTimer.singleShot(0, self.accept)
            return

        self.text_ready.emit(text)
        QTimer.singleShot(600, self.accept)

    def _on_levels(self, levels: list):
        pass   # bars removed — nothing to update

    def _on_status(self, msg: str):
        self._status_label.setText(msg)

    def _on_silence_progress(self, progress: float):
        self._silence_ring.set_progress(progress, visible=True)
        remaining = int(SILENCE_SECONDS * (1 - progress)) + 1
        self._status_label.setText(f"Silence detected… stopping in {remaining}s")

    def _on_silence_ended(self):
        self._silence_ring.set_progress(0.0, visible=False)
        self._waveform.set_active(False)
        self._recording = False
        self._status_label.setText("Transcribing…")

    def _on_error(self, msg: str):
        self._status_label.setText(f"⚠ {msg}")
        self._status_label.setStyleSheet("color: #DC2626; background: transparent;")
        self._recording = False
        self._waveform.set_active(False)

    def _on_close(self):
        if self._recording:
            self._worker.stop_recording()
            self._recording = False
            self._waveform.set_active(False)
        self.reject()

    # ── Re-open reset ────────────────────────
    def showEvent(self, event):
        super().showEvent(event)
        self._text_edit.clear()
        self._silence_ring.set_progress(0.0, visible=False)
        self._status_label.setStyleSheet("color: #7C3AED; background: transparent;")
        if self._triggered_by_wake_word:
            self._status_label.setText("Wake word detected...")
            QTimer.singleShot(0, self._start_recording)
        elif self._model_loaded and not self._recording:
            self._status_label.setText("Listening…")
            QTimer.singleShot(200, self._start_recording)
        else:
            self._status_label.setText("Loading model…")

    def closeEvent(self, event):
        if self._recording:
            self._worker.stop_recording()
            self._recording = False
        super().closeEvent(event)

    def reject(self):
        if self._recording:
            self._worker.stop_recording()
            self._recording = False
            self._waveform.set_active(False)
        super().reject()

    # ── Gradient header paint ────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        card_rect   = self.rect().adjusted(12, 12, -12, -12)
        header_rect = QRect(card_rect.x(), card_rect.y(), card_rect.width(), 60)

        path = QPainterPath()
        path.moveTo(header_rect.x() + 18, header_rect.y())
        path.lineTo(header_rect.right() - 18, header_rect.y())
        path.arcTo(header_rect.right() - 36, header_rect.y(), 36, 36, 90, -90)
        path.lineTo(header_rect.right(), header_rect.bottom())
        path.lineTo(header_rect.x(), header_rect.bottom())
        path.arcTo(header_rect.x(), header_rect.y(), 36, 36, 180, -90)
        path.closeSubpath()

        grad = QLinearGradient(header_rect.topLeft(), header_rect.topRight())
        grad.setColorAt(0, QColor("#7C3AED"))
        grad.setColorAt(1, QColor("#9D5CF6"))
        p.fillPath(path, QBrush(grad))
        p.end()


# ─────────────────────────────────────────────
#  Helper
# ─────────────────────────────────────────────
def open_speech_popup(
    parent=None,
    whisper_model_dir: str = None,
    triggered_by_wake_word: bool = False,
    wake_word_detector: object = None,
) -> str | None:
    popup = SpeechPopup(
        parent=parent,
        whisper_model_dir=whisper_model_dir,
        triggered_by_wake_word=triggered_by_wake_word,
        wake_word_detector=wake_word_detector,
    )
    popup.exec()
    if popup.result() == QDialog.Accepted:
        return popup._text_edit.toPlainText().strip() or None
    return None


# ─────────────────────────────────────────────
#  Standalone test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from PySide6.QtWidgets import QMainWindow, QLineEdit, QPushButton

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    class Demo(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("GemServe Demo")
            self.setFixedSize(400, 120)
            central = QWidget()
            self.setCentralWidget(central)
            layout = QHBoxLayout(central)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(10)

            self.line = QLineEdit()
            self.line.setPlaceholderText("Type your message…")
            self.line.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #DDD6FE; 
                    border-radius: 10px;
                    padding: 8px 12px; 
                    font-size: 13px;
                }
            """)
            mic = QPushButton("🎙")
            mic.setFixedSize(40, 40)
            mic.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #7C3AED, stop:1 #9D5CF6);
                    color: white; 
                    border: none; 
                    border-radius: 20px; 
                    font-size: 16px;
                }
                QPushButton:hover { background: #6D28D9; }
            """)
            self._popup = None
            mic.clicked.connect(self._on_mic)
            layout.addWidget(self.line)
            layout.addWidget(mic)

        def _on_mic(self):
            if self._popup is None:
                self._popup = SpeechPopup(self)
                self._popup.text_ready.connect(self._on_text)
            self._popup.show()

        def _on_text(self, text: str):
            self.line.setText(text)

    w = Demo()
    w.show()
    sys.exit(app.exec())