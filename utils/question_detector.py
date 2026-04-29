# ============================================================
# UTILS / QUESTION_DETECTOR.PY
# Detects if a transcript is an interview question worth answering
# Handles: direct questions, behavioral, coding, and statements
# ============================================================

import re
from logger import logger

# -------- Filler words to ignore --------
FILLER_WORDS = {
    "uh", "um", "hmm", "hm", "ah", "oh", "okay", "ok",
    "yeah", "yes", "no", "alright", "right", "sure", "so",
    "like", "you know", "i mean", "basically", "actually"
}

# -------- Question starters --------
QUESTION_STARTERS = (
    "who", "what", "when", "where", "why", "how",
    "tell me", "explain", "describe", "can you", "could you",
    "would you", "do you", "are you", "have you", "did you",
    "is there", "what's", "whats", "walk me through",
    "talk me through", "give me", "share", "list",
    "define", "compare", "differentiate", "contrast",
)

# -------- Coding / task keywords --------
CODING_KEYWORDS = (
    "write a", "write the", "code", "program", "function", "algorithm",
    "implement", "build", "create a", "design a", "solve",
    "find", "check if", "detect", "reverse", "sort", "search",
    "fibonacci", "factorial", "prime", "palindrome", "anagram",
    "linked list", "binary tree", "stack", "queue", "recursion",
    "complexity", "big o", "time complexity", "space complexity",
    "debug", "fix this", "what's wrong", "optimize",
)


def is_noise(text: str) -> bool:
    """Returns True if transcript is just filler/noise."""
    cleaned = text.strip().lower()
    if len(cleaned.split()) < 3:
        logger.debug(f"[QD] Ignored (too short): '{text}'")
        return True
    words = set(cleaned.split())
    if words.issubset(FILLER_WORDS):
        logger.debug(f"[QD] Ignored (filler only): '{text}'")
        return True
    return False


def is_question(text: str) -> bool:
    """Returns True if transcript is a direct question."""
    cleaned = text.strip().lower()
    if cleaned.endswith("?"):
        logger.debug(f"[QD] Detected (question mark): '{text}'")
        return True
    for starter in QUESTION_STARTERS:
        if cleaned.startswith(starter):
            logger.debug(f"[QD] Detected (starter '{starter}'): '{text}'")
            return True
    return False


def is_coding_task(text: str) -> bool:
    """Returns True if transcript sounds like a coding/task request."""
    cleaned = text.strip().lower()
    for keyword in CODING_KEYWORDS:
        if keyword in cleaned:
            logger.debug(f"[QD] Detected coding task (keyword '{keyword}'): '{text}'")
            return True
    return False


def process_transcript(text: str) -> str | None:
    """
    Main entry point — pass every FINAL transcript here.
    Returns cleaned transcript if it's worth answering, else None.
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    if is_noise(text):
        return None

    if is_question(text):
        logger.info(f"[QD] Question detected: '{text}'")
        return text

    if is_coding_task(text):
        logger.info(f"[QD] Coding task detected: '{text}'")
        return text

    logger.debug(f"[QD] Not actionable, skipping: '{text}'")
    return None