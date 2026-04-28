

# This is working fine for audio received from external sources , but it is not recognising audio produced by laptop's speakers 


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
# [  29/04/26 - 12:20 AM ]  
# Tried this WASAPI loopback method to capture system audio, but it doesn't seem to work. Keeping it here for reference in case we want to revisit.

import sounddevice as sd
import numpy as np
from logger import logger


def list_devices():
    print("\nAvailable audio devices:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  [{i}] {device['name']}")
    print()


def get_device_index(name_hint: str = None):
    if not name_hint:
        return None
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if name_hint.lower() in device['name'].lower():
            return i
    return None


def start_mic_stream(device=None, loopback=False):
    """
    Start audio input stream.
    - device: device index or None for default
    - loopback: if True, capture system audio via WASAPI loopback
    """
    logger.info("Starting audio stream...")

    if loopback:
        # WASAPI loopback — captures system audio (YouTube, Meet, etc.)
        #import sounddevice as sd

        # Find the WASAPI speaker device
        wasapi_speaker = None
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if 'speaker' in d['name'].lower() and 'wasapi' in str(d.get('hostapi', '')):
                wasapi_speaker = i
                break

        # Use device 8 directly if search fails
        if wasapi_speaker is None:
            wasapi_speaker = 8

        logger.info(f"Using WASAPI loopback on device {wasapi_speaker}")

        stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="int16",
            blocksize=1024,
            device=wasapi_speaker,
            extra_settings=sd.WasapiSettings(loopback=True)  # ← key line
        )
    else:
        # Normal mic input
        stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="int16",
            blocksize=1024,
            device=device
        )

    stream.start()
    logger.info("Audio stream started")

    def generator():
        try:
            while True:
                chunk, _ = stream.read(1024)
                yield chunk.tobytes()
        except KeyboardInterrupt:
            logger.info("Stopping audio stream...")
            stream.stop()
            stream.close()

    return generator()


''' 





  




            


'''
# dump -- Not sure why this is commented out, but keeping it here for reference


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