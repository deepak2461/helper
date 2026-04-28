import fitz  # pymupdf
import os
from logger import logger


def load_text_file(path: str) -> str:
    """Read a plain .txt file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_pdf_file(path: str) -> str:
    """Extract text from a PDF file."""
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


def load_file(path: str) -> str:
    """Auto-detect file type and load it."""
    if not os.path.exists(path):
        logger.warning(f"[CTX] File not found: {path}")
        return ""

    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        logger.info(f"[CTX] Loading PDF: {path}")
        return load_pdf_file(path)
    elif ext in (".txt", ".md"):
        logger.info(f"[CTX] Loading text file: {path}")
        return load_text_file(path)
    else:
        logger.warning(f"[CTX] Unsupported file type: {ext}")
        return ""


def load_context(resume_path: str = "resume.pdf", jd_path: str = "jd.pdf") -> dict:
    """
    Load resume and job description from project root.
    Returns a dict with 'resume' and 'jd' keys.
    Falls back gracefully if files are missing.
    """
    resume = load_file(resume_path)
    jd = load_file(jd_path)

    if not resume:
        logger.warning("[CTX] Resume not loaded — answers will be generic")
    else:
        logger.info(f"[CTX] Resume loaded ({len(resume)} chars)")

    if not jd:
        logger.warning("[CTX] Job description not loaded — answers will be generic")
    else:
        logger.info(f"[CTX] Job description loaded ({len(jd)} chars)")

    return {"resume": resume, "jd": jd}