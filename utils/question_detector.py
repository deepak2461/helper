import re
from logger import logger

# Filler words / noise to ignore entirely
FILLER_WORDS = {
    "uh", "um", "hmm", "hm", "ah", "oh", "okay", "ok",
    "yeah", "yes", "no", "alright", "right", "sure", "so",
    "like", "you know", "i mean", "basically", "actually"
}

# Question trigger words/phrases at the start of a sentence
QUESTION_STARTERS = (
    "who", "what", "when", "where", "why", "how",
    "tell me", "explain", "describe", "can you", "could you",
    "would you", "do you", "are you", "have you", "did you",
    "is there", "what's", "whats", "walk me through",
    "talk me through", "give me", "share"
)


def is_noise(text: str) -> bool:
    """Returns True if the transcript is just filler/noise — ignore these."""
    cleaned = text.strip().lower()

    # Too short — less than 3 words
    if len(cleaned.split()) < 3:
        logger.debug(f"[QD] Ignored (too short): '{text}'")
        return True

    # Entire transcript is just filler words
    words = set(cleaned.split())
    if words.issubset(FILLER_WORDS):
        logger.debug(f"[QD] Ignored (filler only): '{text}'")
        return True

    return False


def is_question(text: str) -> bool:
    """Returns True if the transcript looks like an interview question."""
    cleaned = text.strip().lower()

    # Ends with a question mark
    if cleaned.endswith("?"):
        logger.debug(f"[QD] Detected (question mark): '{text}'")
        return True

    # Starts with a known question word/phrase
    for starter in QUESTION_STARTERS:
        if cleaned.startswith(starter):
            logger.debug(f"[QD] Detected (starter '{starter}'): '{text}'")
            return True

    return False


def process_transcript(text: str) -> str | None:
    """
    Main entry point. Pass every FINAL transcript here.

    Returns:
        - The cleaned transcript string if it's a valid question
        - None if it should be ignored
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    if is_noise(text):
        return None

    if is_question(text):
        logger.info(f"[QD] Question detected: '{text}'")
        return text

    # Not clearly a question — log and skip for now
    # (Later we can send ambiguous ones to LLM for classification)
    logger.debug(f"[QD] Not a question, skipping: '{text}'")
    return None