# ============================================================
# STT / DEEPGRAM_CLIENT.PY
# Deepgram streaming STT
# Supports:
#   - Auto mode: always listening, detects questions automatically
#   - Manual mode: buffer all speech between START and STOP,
#                  send full buffer to LLM regardless of question detection
# ============================================================

import threading
import time
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents

from logger import logger
from config import DEEPGRAM_API_KEY
from utils.question_detector import process_transcript


class DeepgramSTT:
    def __init__(self, answer_engine=None):
        self.deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)
        self.answer_engine = answer_engine

        # -------- Mode control --------
        self.manual_mode = False
        self.manual_listening = False
        self.mode_lock = threading.Lock()  # Thread-safe mode switching

        # -------- Manual mode text buffer --------
        # Accumulates all finals between START and STOP
        self.manual_buffer = []
        
        # -------- Keep-alive tracking --------
        self.last_audio_time = None
        self.connection = None
        self.connection_lock = threading.Lock()
        self.reconnect_event = threading.Event()

    # -------- Set mode (called from UI) --------
    def set_mode(self, manual: bool):
        with self.mode_lock:
            self.manual_mode = manual
            self.manual_listening = False
            self.manual_buffer = []
            logger.info(f"[STT] Mode set to: {'MANUAL' if manual else 'AUTO'}")

    # -------- Manual START — begin buffering --------
    def start_manual(self):
        with self.mode_lock:
            self.manual_listening = True
            self.manual_buffer = []  # clear previous buffer
            logger.info("[STT] Manual: START listening")

    # -------- Manual STOP — flush buffer to LLM --------
    def stop_manual(self):
        with self.mode_lock:
            self.manual_listening = False
            full_text = " ".join(self.manual_buffer).strip()
            self.manual_buffer = []
            logger.info(f"[STT] Manual: STOP. Buffer: '{full_text}'")

        if full_text and self.answer_engine:
            logger.info(f"[STT] Sending manual buffer to LLM: '{full_text}'")
            threading.Thread(
                target=self.answer_engine.generate,
                args=(full_text,),
                daemon=True
            ).start()

    # -------- Process a final transcript --------
    def handle_transcript(self, transcript: str):
        from server.socket_server import send_to_clients

        send_to_clients({"type": "speech_activity"})

        with self.mode_lock:
            is_manual = self.manual_mode
            is_listening = self.manual_listening
        
        if is_manual:
            if is_listening:
                # -------- Buffer everything in manual mode --------
                self.manual_buffer.append(transcript)
                logger.debug(f"[STT] Buffered (manual): '{transcript}'")
            else:
                # In manual mode but not listening - ignore transcript
                logger.debug(f"[STT] Ignored (manual mode, not listening): '{transcript}'")
        else:
            # -------- Auto mode: detect question and answer --------
            question = process_transcript(transcript)
            if question and self.answer_engine:
                logger.info(f"[STT] Question detected (auto mode): '{question}'")
                threading.Thread(
                    target=self.answer_engine.generate,
                    args=(question,),
                    daemon=True
                ).start()
            else:
                logger.debug(f"[STT] Not a question (auto mode): '{transcript}'")

    # -------- Notify UI of timeout status --------
    def notify_ui_timeout(self, remaining_secs):
        """Notify UI of remaining time before connection timeout"""
        from server.socket_server import send_to_clients
        send_to_clients({"type": "timeout_warning", "remaining": remaining_secs})

    def extend_timeout(self):
        """User-triggered keep-alive from the UI timer button."""
        with self.connection_lock:
            connection = self.connection

        if not connection:
            logger.warning("[STT] Timer reset requested but Deepgram is not connected")
            return

        try:
            silent_frame = b'\x00' * 3200  # ~100ms of silence at 16kHz
            connection.send(silent_frame)
            self.last_audio_time = time.time()
            logger.info("[STT] Timer reset keep-alive sent")
        except Exception as e:
            logger.error(f"[STT] Timer reset keep-alive failed: {e}")

    def reconnect(self):
        """Reconnect after Deepgram has timed out or disconnected."""
        with self.connection_lock:
            is_connected = self.connection is not None

        if is_connected:
            logger.info("[STT] Reconnect requested while already connected")
            return

        logger.info("[STT] Reconnect requested")
        self.reconnect_event.set()
        self._notify_ui({"type": "stt_reconnecting"})

    def _notify_ui(self, message: dict):
        from server.socket_server import send_to_clients

        send_to_clients(message)

    # -------- Main STT run loop --------
    def run(self, audio_generator):
        while True:
            self._run_connection(audio_generator)
            logger.warning("[STT] Deepgram disconnected; waiting for reconnect request")
            self._notify_ui({"type": "stt_disconnected"})
            self.reconnect_event.clear()
            self.reconnect_event.wait()
            self._notify_ui({"type": "stt_reconnecting"})

    def _run_connection(self, audio_generator):
        logger.info("[STT] Connecting to Deepgram...")

        connection = self.deepgram.listen.websocket.v("1")
        connection_closed = threading.Event()
        with self.connection_lock:
            self.connection = connection

        # -------- Event: Connection opened --------
        def on_open(self_inner, open_obj, **kwargs):
            logger.info("[STT] Deepgram connection opened")
            self.last_audio_time = time.time()
            self._notify_ui({"type": "stt_connected"})

        # -------- Event: Transcript received --------
        def on_message(self_inner, result, **kwargs):
            try:
                transcript = result.channel.alternatives[0].transcript
                is_final = result.is_final

                if transcript.strip():
                    if not is_final:
                        # -------- Show live partial in terminal --------
                        print(f"\r🎤 {transcript}    ", end="", flush=True)
                    else:
                        print(f"\r✅ {transcript}        ")
                        logger.info(f"[STT] Final: {transcript}")
                        self.handle_transcript(transcript)

            except Exception as e:
                logger.error(f"[STT] Message error: {e}")

        # -------- Event: Connection closed --------
        def on_close(self_inner, close_obj, **kwargs):
            logger.warning("[STT] Deepgram connection closed")
            connection_closed.set()

        # -------- Event: Error --------
        def on_error(self_inner, error, **kwargs):
            logger.error(f"[STT] Deepgram error: {error}")
            connection_closed.set()

        connection.on(LiveTranscriptionEvents.Open, on_open)
        connection.on(LiveTranscriptionEvents.Transcript, on_message)
        connection.on(LiveTranscriptionEvents.Close, on_close)
        connection.on(LiveTranscriptionEvents.Error, on_error)

        # -------- Start connection --------
        options = LiveOptions(
            model="nova-2",
            language="en",
            encoding="linear16",
            sample_rate=16000,
            channels=1,
            interim_results=True,
            punctuate=True,
            endpointing=2500,  # Increased from 1500ms to 2500ms to handle word gaps better
            utterance_end_ms=3000,  # Increased from 2000ms to 3000ms to wait longer before closing
        )

        if not connection.start(options):
            logger.error("[STT] Failed to start Deepgram connection")
            with self.connection_lock:
                if self.connection is connection:
                    self.connection = None
            return

        logger.info("[STT] Deepgram started. Listening...")
        self.last_audio_time = time.time()

        # -------- Audio stream loop --------
        try:
            for chunk in audio_generator:
                if connection_closed.is_set():
                    break
                self.last_audio_time = time.time()
                connection.send(chunk)
        except KeyboardInterrupt:
            logger.info("[STT] Stopping...")
        except Exception as e:
            logger.error(f"[STT] Stream error: {e}")
        finally:
            connection.finish()
            with self.connection_lock:
                if self.connection is connection:
                    self.connection = None
            logger.info("[STT] Deepgram finished")
