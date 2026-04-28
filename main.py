from audio.mic_stream import start_mic_stream
from logger import logger
#import asyncio
#from audio.mic_stream import async_audio_stream
from stt.deepgram_client import DeepgramClient
from stt.deepgram_client import DeepgramSTT
from dotenv import load_dotenv


def main():
    logger.info("Starting STT test with Deepgram SDK...")
    load_dotenv()

    logger.info("Loading Deepgram API key...")

    stt = DeepgramSTT()
    audio_stream = start_mic_stream()

    stt.run(audio_stream)


if __name__ == "__main__":
    main()