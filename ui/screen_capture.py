# ============================================================
# UI / SCREEN_CAPTURE.PY
# Screenshot + OCR for coding problem detection
# Called when user clicks "Capture Screen" button in UI
# ============================================================

import threading
from PIL import ImageGrab
from logger import logger

# -------- Lazy Load EasyOCR --------
_reader = None

def get_reader():
    """Load EasyOCR reader once (lazy, heavy to load)."""
    global _reader
    if _reader is None:
        logger.info("[OCR] Loading EasyOCR reader...")
        import easyocr
        _reader = easyocr.Reader(['en'], gpu=False)
        logger.info("[OCR] EasyOCR reader ready")
    return _reader


# -------- Take Screenshot --------
def take_screenshot():
    """Capture full screen and return PIL Image."""
    try:
        img = ImageGrab.grab()
        logger.info(f"[OCR] Screenshot taken: {img.size}")
        return img
    except Exception as e:
        logger.error(f"[OCR] Screenshot failed: {e}")
        return None


# -------- Extract Text from Image --------
def extract_text(image) -> str:
    """Run OCR on PIL Image and return extracted text."""
    try:
        reader = get_reader()
        results = reader.readtext(image, detail=0, paragraph=True)
        text = "\n".join(results).strip()
        logger.info(f"[OCR] Extracted {len(text)} chars from screen")
        return text
    except Exception as e:
        logger.error(f"[OCR] OCR failed: {e}")
        return ""


# -------- Full Pipeline: Screenshot → OCR → Return Text --------
def capture_and_extract() -> str:
    """Take screenshot and extract all text from it."""
    image = take_screenshot()
    if not image:
        return ""
    return extract_text(image)