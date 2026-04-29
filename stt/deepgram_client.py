# ============================================================
# STT / DEEPGRAM_CLIENT.PY
# Deepgram streaming STT client
# Supports two modes:
#   - Auto: always listening, detects questions automatically
#   - Manual: only processes audio between START and STOP signals
# ============================================================

import threading
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents

from logger import logger
from config import DEEPGRAM_API_KEY
from utils.question_detector import process_transcript


class DeepgramSTT:
    def __init__(self, answer_engine=None):
        self.deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)
        self.answer_engine = answer_engine

        # -------- Mode Control --------
        self.manual_mode = False       # False = auto, True = manual
        self.manual_listening = False  # True = currently capturing in manual mode

    # -------- Manual Mode: Start Listening --------
    def start_manual(self):
        self.manual_listening = True
        logger.info("[STT] Manual mode: START listening")

    # -------- Manual Mode: Stop Listening --------
    def stop_manual(self):
        self.manual_listening = False
        logger.info("[STT] Manual mode: STOP listening")

    # -------- Set Mode --------
    def set_mode(self, manual: bool):
        self.manual_mode = manual
        self.manual_listening = False
        mode = "MANUAL" if manual else "AUTO"
        logger.info(f"[STT] Mode set to: {mode}")

    # -------- Process Question + Generate Answer --------
    def handle_question(self, transcript: str):
        question = process_transcript(transcript)
        if question:
            logger.info(f"[STT] Question detected: {question}")
            if self.answer_engine:
                self.answer_engine.generate(question)

    # -------- Main STT Run Loop --------
    def run(self, audio_generator):
        logger.info("[STT] Connecting to Deepgram...")

        connection = self.deepgram.listen.websocket.v("1")

        # -------- Event: Connection Opened --------
        def on_open(self_inner, open_obj, **kwargs):
            logger.info("[STT] Deepgram connection opened")

        # -------- Event: Transcript Received --------
        def on_message(self_inner, result, **kwargs):
            try:
                transcript = result.channel.alternatives[0].transcript
                is_final = result.is_final

                if transcript.strip():
                    if not is_final:
                        print(f"\r🎤 {transcript}    ", end="", flush=True)
                    else:
                        print(f"\r✅ {transcript}        ")
                        logger.info(f"[STT] Final: {transcript}")

                        # -------- Auto Mode: always process --------
                        if not self.manual_mode:
                            self.handle_question(transcript)

                        # -------- Manual Mode: only process if listening --------
                        elif self.manual_mode and self.manual_listening:
                            self.handle_question(transcript)

            except Exception as e:
                logger.error(f"[STT] Message error: {e}")

        # -------- Event: Connection Closed --------
        def on_close(self_inner, close_obj, **kwargs):
            logger.warning("[STT] Deepgram connection closed")

        # -------- Event: Error --------
        def on_error(self_inner, error, **kwargs):
            logger.error(f"[STT] Deepgram error: {error}")

        connection.on(LiveTranscriptionEvents.Open, on_open)
        connection.on(LiveTranscriptionEvents.Transcript, on_message)
        connection.on(LiveTranscriptionEvents.Close, on_close)
        connection.on(LiveTranscriptionEvents.Error, on_error)

        # -------- Start Connection --------
        options = LiveOptions(
            model="nova-2",
            language="en",
            encoding="linear16",
            sample_rate=16000,
            channels=1,
            interim_results=True,
            punctuate=True,
        )

        if not connection.start(options):
            logger.error("[STT] Failed to start Deepgram connection")
            return

        logger.info("[STT] Deepgram started. Listening...")

        # -------- Audio Stream Loop --------
        try:
            for chunk in audio_generator:
                connection.send(chunk)
        except KeyboardInterrupt:
            logger.info("[STT] Stopping...")
        except Exception as e:
            logger.error(f"[STT] Stream error: {e}")
        finally:
            connection.finish()
            logger.info("[STT] Deepgram connection finished")