# ============================================================
# UI / SCREEN_CAPTURE.PY
# Screenshot + OCR for coding problem detection
# Saves screenshots to /screenshots folder with timestamps
# ============================================================

import numpy as np
import os
from datetime import datetime
from PIL import ImageGrab
from logger import logger

# -------- Screenshots save folder --------
SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# -------- Lazy Load EasyOCR --------
_reader = None


def get_reader():
    """Load EasyOCR reader once — heavy, so load lazily."""
    global _reader
    if _reader is None:
        logger.info("[OCR] Loading EasyOCR reader (first time, may take a moment)...")
        import easyocr
        _reader = easyocr.Reader(['en'], gpu=False)
        logger.info("[OCR] EasyOCR reader ready")
    return _reader


# -------- Take Screenshot --------
def take_screenshot():
    """Capture full screen, save to /screenshots, return numpy array."""
    try:
        img = ImageGrab.grab()
        # -------- Save screenshot with timestamp --------
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(SCREENSHOT_DIR, f"screen_{timestamp}.png")
        img.save(save_path)
        logger.info(f"[OCR] Screenshot saved: {save_path} ({img.size})")
        # -------- Convert PIL Image to numpy array (required by EasyOCR) --------
        return np.array(img)
    except Exception as e:
        logger.error(f"[OCR] Screenshot failed: {e}")
        return None


# -------- Extract Text from numpy array --------
def extract_text(image_array) -> str:
    """Run OCR on numpy array and return extracted text."""
    try:
        reader = get_reader()
        results = reader.readtext(image_array, detail=0, paragraph=True)
        text = "\n".join(results).strip()
        logger.info(f"[OCR] Extracted {len(text)} chars from screen")
        return text
    except Exception as e:
        logger.error(f"[OCR] OCR failed: {e}")
        return ""


# -------- Full Pipeline: Screenshot → numpy → OCR → Text --------
def capture_and_extract() -> str:
    """Take screenshot, save it, extract all text from it."""
    image_array = take_screenshot()
    if image_array is None:
        return ""
    return extract_text(image_array)