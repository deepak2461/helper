
# ============================================================
# AUDIO / MIC_STREAM.PY
# Audio capture supporting two modes:
#   1. Microphone (default) — captures voice input
#   2. Speaker loopback — captures ALL system audio (YouTube, Meet, Teams)
#      Uses PyAudioWPatch for WASAPI loopback on Windows
# ============================================================

import numpy as np
from logger import logger

SAMPLE_RATE = 16000
CHUNK_SIZE = 1024


# -------- List available audio devices --------
def list_audio_devices():
    import pyaudiowpatch as pyaudio
    p = pyaudio.PyAudio()
    print("\nAvailable audio devices:")
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        if d['maxInputChannels'] > 0:
            print(f"  [{i}] {d['name']}")
    p.terminate()


# -------- Find default WASAPI loopback device (speaker output) --------
def find_loopback_device():
    """Find the default speaker's WASAPI loopback virtual device."""
    import pyaudiowpatch as pyaudio
    p = pyaudio.PyAudio()
    try:
        # Get default output device
        default_output = p.get_default_wasapi_loopback()
        logger.info(f"[AUDIO] Loopback device found: {default_output['name']}")
        return default_output
    except Exception as e:
        logger.error(f"[AUDIO] Could not find loopback device: {e}")
        return None
    finally:
        p.terminate()


# -------- Mic stream (default — captures microphone) --------
def start_mic_stream():
    """Capture from default microphone using sounddevice."""
    import sounddevice as sd
    logger.info("[AUDIO] Starting microphone stream...")

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=CHUNK_SIZE,
    )
    stream.start()
    logger.info("[AUDIO] Microphone stream started")

    def generator():
        try:
            while True:
                data, _ = stream.read(CHUNK_SIZE)
                yield data.tobytes()
        except KeyboardInterrupt:
            logger.info("[AUDIO] Stopping microphone stream...")
            stream.stop()
            stream.close()

    return generator()


# -------- Speaker loopback stream (captures system audio) --------
def start_loopback_stream():
    """
    Capture system audio output (speakers) using PyAudioWPatch WASAPI loopback.
    Captures everything playing on laptop: YouTube, Meet, Teams, etc.
    Audio is resampled to 16000Hz mono int16 for Deepgram.
    """
    import pyaudiowpatch as pyaudio

    logger.info("[AUDIO] Starting speaker loopback stream...")

    p = pyaudio.PyAudio()

    # -------- Find default loopback device --------
    try:
        loopback_device = p.get_default_wasapi_loopback()
        device_index = loopback_device['index']
        device_rate = int(loopback_device['defaultSampleRate'])
        device_channels = loopback_device['maxInputChannels']
        logger.info(f"[AUDIO] Loopback: {loopback_device['name']} | {device_rate}Hz | {device_channels}ch")
    except Exception as e:
        logger.error(f"[AUDIO] Loopback device not found: {e}. Falling back to mic.")
        p.terminate()
        return start_mic_stream()

    # -------- Open loopback stream --------
    stream = p.open(
        format=pyaudio.paInt16,
        channels=device_channels,
        rate=device_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK_SIZE,
    )

    logger.info("[AUDIO] Speaker loopback stream started — capturing system audio")

    def generator():
        try:
            while True:
                raw = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                audio = np.frombuffer(raw, dtype=np.int16)

                # -------- Convert stereo to mono --------
                if device_channels > 1:
                    audio = audio.reshape(-1, device_channels)
                    audio = audio.mean(axis=1).astype(np.int16)

                # -------- Resample to 16000Hz if needed --------
                if device_rate != SAMPLE_RATE:
                    ratio = SAMPLE_RATE / device_rate
                    new_len = int(len(audio) * ratio)
                    indices = np.linspace(0, len(audio) - 1, new_len)
                    audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.int16)

                yield audio.tobytes()

        except KeyboardInterrupt:
            logger.info("[AUDIO] Stopping loopback stream...")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

    return generator()


# -------- Auto-select mode based on .env or startup prompt --------
def start_audio_stream(mode: str = "mic"):
    """
    mode = 'mic'      → microphone input
    mode = 'loopback' → speaker loopback (system audio)
    mode = 'both'     → mix mic + loopback (future)
    """
    if mode == "loopback":
        return start_loopback_stream()
    else:
        return start_mic_stream()









'''
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