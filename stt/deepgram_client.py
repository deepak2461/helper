import threading
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents

from logger import logger
from config import DEEPGRAM_API_KEY
from utils.question_detector import process_transcript

class DeepgramSTT:
    def __init__(self, answer_engine=None):
        self.deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)
        self.answer_engine = answer_engine

    def run(self, audio_generator):
        logger.info("Connecting to Deepgram...")

        # ✅ v7 uses listen.websocket.v("1") not listen.live.v("1")
        connection = self.deepgram.listen.websocket.v("1")

        # ------------------ EVENT HANDLERS ------------------

        def on_open(self_inner, open_obj, **kwargs):
            logger.info("Deepgram connection opened")

        def on_message(self_inner, result, **kwargs):
            try:
                transcript = result.channel.alternatives[0].transcript
                is_final = result.is_final
                if transcript.strip():
                    if is_final:
                        logger.info(f"[FINAL] {transcript}")

                        question = process_transcript(transcript)
                        if question:
                            logger.info(f"[Question] {question}")
                            if self.answer_engine:
                                answer = self.answer_engine.generate(question)
                                if answer :
                                    logger.info(f"[Answer]\n {answer}")
                            else:
                                logger.warning("No answer engine provided")
                    else:
                        logger.debug(f"[PARTIAL] {transcript}")
            except Exception as e:
                logger.error(f"Error processing transcript: {e}")

        def on_close(self_inner, close_obj, **kwargs):
            logger.warning("Deepgram connection closed")

        def on_error(self_inner, error, **kwargs):
            logger.error(f"Deepgram error: {error}")

        # ------------------ REGISTER EVENTS ------------------

        connection.on(LiveTranscriptionEvents.Open, on_open)
        connection.on(LiveTranscriptionEvents.Transcript, on_message)
        connection.on(LiveTranscriptionEvents.Close, on_close)
        connection.on(LiveTranscriptionEvents.Error, on_error)

        # ------------------ START CONNECTION ------------------

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
            logger.error("Failed to start Deepgram connection. Check your API key.")
            return

        logger.info("Deepgram started. Speak into your mic...")

        # ------------------ AUDIO LOOP ------------------

        try:
            for chunk in audio_generator:
                connection.send(chunk)
                #logger.debug(f"Sent chunk: {len(chunk)} bytes")

        except KeyboardInterrupt:
            logger.info("Stopping STT...")

        except Exception as e:
            logger.error(f"Audio streaming error: {e}")

        finally:
            connection.finish()
            logger.info("Deepgram connection finished.")