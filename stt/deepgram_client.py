import threading
from deepgram import DeepgramClient
from deepgram.core.events import EventType

from logger import logger
from config import DEEPGRAM_API_KEY

DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?encoding=linear16"
    "&sample_rate=16000"
    "&channels=1"
    "&interim_results=true"
    "&punctuate=true"
)

class DeepgramSTT:
    def __init__(self):
        self.client = DeepgramClient(api_key=DEEPGRAM_API_KEY)

    def run(self, audio_generator):
        logger.info("Connecting to Deepgram...")

        with self.client.listen.v1.connect(
            model="nova-2",   # safer than nova-3 for now
            language="en",
        ) as connection:

            #ready_event = threading.Event()

            # ------------------ EVENT HANDLERS ------------------

            def on_open(_):
                logger.info("Deepgram connection opened")
                #ready_event.set()

            def on_message(result):
                try:
                    channel = getattr(result, "channel", None)
                    if not channel:
                        return

                    alternatives = getattr(channel, "alternatives", [])
                    if not alternatives:
                        return

                    transcript = alternatives[0].transcript
                    is_final = getattr(result, "is_final", False)

                    if transcript.strip():
                        if is_final:
                            logger.info(f"[FINAL] {transcript}")
                        else:
                            logger.debug(f"[PARTIAL] {transcript}")

                except Exception as e:
                    logger.error(f"Error processing transcript: {e}")

            def on_close(_):
                logger.warning("Deepgram connection closed")

            def on_error(error):
                logger.error(f"Deepgram error: {error}")

            # ------------------ REGISTER EVENTS ------------------

            connection.on(EventType.OPEN, on_open)
            connection.on(EventType.MESSAGE, on_message)
            connection.on(EventType.CLOSE, on_close)
            connection.on(EventType.ERROR, on_error)

            # ------------------ START ------------------

            connection.start_listening()

            logger.info("Streaming audio to Deepgram... immediate")
            #ready_event.wait()

            #logger.info("Streaming audio to Deepgram...")

            # ------------------ AUDIO LOOP ------------------
            '''
            try:
                for chunk in audio_generator:
                    logger.debug(f"Sending audio chunk: {len(chunk)} bytes")  # comment this later
                    connection.send_media(chunk)

            except KeyboardInterrupt:
                logger.info("Stopping STT...")

            except Exception as e:
                logger.error(f"Error sending audio: {e}")

            '''
            def stream_audio():
                try:
                    for chunk in audio_generator:
                        logger.debug(f"Sending audio chunk: {len(chunk)} bytes")  # comment this later
                        connection.send_media(chunk)
                except Exception as e:
                    logger.error(f"Audio streaming error: {e}")

            audio_thread = threading.Thread(target=stream_audio, daemon=True)
            audio_thread.start()

        # ------------------ KEEP MAIN THREAD ALIVE ------------------

            try:
                audio_thread.join()
            except KeyboardInterrupt:
                logger.info("Stopping STT...")