from audio.mic_stream import start_mic_stream
from logger import logger
from stt.deepgram_client import DeepgramSTT
from utils.context_loader import load_context
from llm.answer_engine import AnswerEngine
from dotenv import load_dotenv

def main():
    load_dotenv()
    logger.info("Starting Helper...")

    ## Added below 5 lines while trying to capture system audio, but it is not working yet. Will debug later. [  29/04/26 - 12:20 AM ]
    # print("\nAudio mode:")
    # print("  [1] Microphone (default) — captures your voice + nearby sounds")
    # print("  [2] System audio loopback — captures YouTube, Meet, Zoom etc.")
    # choice = input("\nChoose mode (1 or 2): ").strip()
    # loopback = choice == "2"

    # Load resume + JD
    context = load_context(resume_path="docs/resume.pdf", jd_path="docs/jd.pdf")

    # Init LLM engine
    engine = AnswerEngine(resume=context["resume"], jd=context["jd"])

    # Init STT
    stt = DeepgramSTT(answer_engine=engine)

    # Start mic + run
    audio_stream = start_mic_stream()
    stt.run(audio_stream)


if __name__ == "__main__":
    main()