# ============================================================
# STT / DEEPGRAM_CLIENT.PY
# Deepgram streaming STT
# Supports:
#   - Auto mode: always listening, detects questions automatically
#   - Manual mode: buffer all speech between START and STOP,
#                  send full buffer to LLM regardless of question detection
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

        # -------- Mode control --------
        self.manual_mode = False
        self.manual_listening = False

        # -------- Manual mode text buffer --------
        # Accumulates all finals between START and STOP
        self.manual_buffer = []

    # -------- Set mode (called from UI) --------
    def set_mode(self, manual: bool):
        self.manual_mode = manual
        self.manual_listening = False
        self.manual_buffer = []
        logger.info(f"[STT] Mode set to: {'MANUAL' if manual else 'AUTO'}")

    # -------- Manual START — begin buffering --------
    def start_manual(self):
        self.manual_listening = True
        self.manual_buffer = []  # clear previous buffer
        logger.info("[STT] Manual: START listening")

    # -------- Manual STOP — flush buffer to LLM --------
    def stop_manual(self):
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
        if self.manual_mode:
            if self.manual_listening:
                # -------- Buffer everything in manual mode --------
                self.manual_buffer.append(transcript)
                logger.debug(f"[STT] Buffered: '{transcript}'")
        else:
            # -------- Auto mode: detect question and answer --------
            question = process_transcript(transcript)
            if question and self.answer_engine:
                threading.Thread(
                    target=self.answer_engine.generate,
                    args=(question,),
                    daemon=True
                ).start()

    # -------- Main STT run loop --------
    def run(self, audio_generator):
        logger.info("[STT] Connecting to Deepgram...")

        connection = self.deepgram.listen.websocket.v("1")

        # -------- Event: Connection opened --------
        def on_open(self_inner, open_obj, **kwargs):
            logger.info("[STT] Deepgram connection opened")

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

        # -------- Event: Error --------
        def on_error(self_inner, error, **kwargs):
            logger.error(f"[STT] Deepgram error: {error}")

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
            endpointing=1500,
            utterance_end_ms=2000,
        )

        if not connection.start(options):
            logger.error("[STT] Failed to start Deepgram connection")
            return

        logger.info("[STT] Deepgram started. Listening...")

        # -------- Audio stream loop --------
        try:
            for chunk in audio_generator:
                connection.send(chunk)
        except KeyboardInterrupt:
            logger.info("[STT] Stopping...")
        except Exception as e:
            logger.error(f"[STT] Stream error: {e}")
        finally:
            connection.finish()
            logger.info("[STT] Deepgram finished")