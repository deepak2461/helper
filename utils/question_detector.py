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

LEADING_FILLERS = ("okay", "ok", "so", "yeah", "yes", "right", "well")
WEAK_CONFIRMATIONS = ("okay", "ok", "right", "correct", "yeah", "yes")
ANNOUNCEMENT_PREFIXES = (
    "i will ", "i'm going to ", "i am going to ", "i am pasting ",
    "i'm pasting ", "give me a second", "let me ", "you can ",
)


def is_screen_capture_command(text: str) -> bool:
    """Return True for an imperative request to capture the current screen."""
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return bool(re.search(
        r"\b(?:take|capture|grab)\b[^.?!]{0,30}\b(?:screenshot|screen)\b",
        cleaned,
    ))

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
    question_text = re.sub(
        r"^(?:(?:okay|ok|so|yeah|yes|right|well)[,.]?\s+)+",
        "",
        cleaned,
    ).strip()
    without_confirmation = re.sub(
        r"(?:\s+(?:okay|ok|right|correct|yeah|yes))\s*\?+$",
        "?",
        cleaned,
    ).strip()
    if without_confirmation.endswith("?") and without_confirmation != "?":
        if any(cleaned.endswith(f" {confirmation}?") for confirmation in WEAK_CONFIRMATIONS):
            meaningful = without_confirmation[:-1].strip()
            if not any(starter in meaningful for starter in QUESTION_STARTERS):
                return False
        logger.debug(f"[QD] Detected (question mark): '{text}'")
        return True
    for starter in QUESTION_STARTERS:
        if question_text.startswith(starter):
            logger.debug(f"[QD] Detected (starter '{starter}'): '{text}'")
            return True
    return False


def is_coding_task(text: str) -> bool:
    """Returns True if transcript sounds like a coding/task request."""
    cleaned = text.strip().lower()
    explicit_task = (
        "write code", "write a program", "write a function", "provide code",
        "implement", "build", "create a", "design a", "solve", "debug",
        "fix this", "optimize", "algorithm for", "how would you code",
    )
    if any(phrase in cleaned for phrase in explicit_task):
        logger.debug(f"[QD] Detected coding task: '{text}'")
        return True
    for keyword in CODING_KEYWORDS:
        if keyword in ("fibonacci", "factorial", "prime", "palindrome", "anagram",
                       "linked list", "binary tree", "stack", "queue", "recursion",
                       "big o", "time complexity", "space complexity") and keyword in cleaned:
            logger.debug(f"[QD] Detected coding task (keyword '{keyword}'): '{text}'")
            return True
    return False


def normalize_transcript(text: str) -> str:
    """Normalize common spoken filler and a few stable STT terminology errors."""
    normalized = re.sub(r"\s+", " ", text.strip())
    normalized = re.sub(r"\b[Ss]\s+three\b", "S3", normalized)
    normalized = re.sub(r"\b[Ll]{2,3}[Mm]\b", "LLM", normalized)
    return normalized


def is_announcement(text: str) -> bool:
    """Reject setup or confirmation statements that are not requests for an answer."""
    cleaned = text.strip().lower()
    if any(cleaned.startswith(prefix) for prefix in ANNOUNCEMENT_PREFIXES):
        return True
    words = cleaned.rstrip("?").split()
    if len(words) <= 5 and words and words[-1] in WEAK_CONFIRMATIONS:
        return True
    return False


def process_transcript(text: str) -> str | None:
    """
    Main entry point — pass every FINAL transcript here.
    Returns cleaned transcript if it's worth answering, else None.
    """
    if not text or not text.strip():
        return None

    text = normalize_transcript(text)

    if is_noise(text):
        return None

    if is_announcement(text):
        logger.debug(f"[QD] Ignored announcement: '{text}'")
        return None

    if is_question(text):
        logger.info(f"[QD] Question detected: '{text}'")
        return text

    if is_coding_task(text):
        logger.info(f"[QD] Coding task detected: '{text}'")
        return text

    logger.debug(f"[QD] Not actionable, skipping: '{text}'")
    return None