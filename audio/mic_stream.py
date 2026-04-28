import sounddevice as sd
import numpy as np
from logger import logger



SAMPLE_RATE = 16000
CHUNK_SIZE = 1024  # smaller, more frequent chunks'


def start_mic_stream():
    logger.info("Starting microphone stream (blocking mode)...")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",   # IMPORTANT: directly int16
        blocksize=CHUNK_SIZE,
    ) as stream:

        logger.info("Microphone stream started")

        try:
            while True:
                data, _ = stream.read(CHUNK_SIZE)

                # already int16 → just convert to bytes
                audio_bytes = data.tobytes()

                yield audio_bytes

        except KeyboardInterrupt:
            logger.info("Stopping microphone stream...")



            


'''
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.1  # 100ms
channels = 1
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
dtype = np.float32

import asyncio


async def async_audio_stream():
    for chunk in start_mic_stream():
        yield chunk
        await asyncio.sleep(0)

def audio_callback(indata, frames, time, status):
    if status:
        logger.warning(f"Audio status: {status}")

    # Convert to mono if needed
    audio_data = indata[:, 0]

    # Convert to bytes (16-bit PCM)
    audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()

    # Push to queue (handled externally)
    audio_callback.queue.append(audio_bytes)


def start_mic_stream():
    logger.info("Starting microphone stream...")

    audio_callback.queue = []

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=audio_callback,
        blocksize=CHUNK_SIZE
    )

    stream.start()

    logger.info("Microphone stream started")

    try:
        while True:
            if audio_callback.queue:
                chunk = audio_callback.queue.pop(0)
                yield chunk
    except KeyboardInterrupt:
        logger.info("Stopping microphone stream...")
        stream.stop()


        '''   