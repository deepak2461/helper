# ============================================================
# UI / TRAY.PY
# System tray icon — right click to show/quit app
# Ensures app can be closed even when hidden from taskbar
# ============================================================

import threading
import pystray
from PIL import Image, ImageDraw
from logger import logger


def create_tray_icon():
    """Create a simple colored circle as tray icon."""
    img = Image.new("RGB", (64, 64), color="#0d0d14")
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill="#818cf8")
    return img


def start_tray(overlay_root_ref: list):
    """
    Start system tray icon in background thread.
    overlay_root_ref is a list holding [root] so we can call root.deiconify().
    """
    def on_show(icon, item):
        root = overlay_root_ref[0]
        if root:
            root.deiconify()  # bring window back if hidden
            root.attributes("-topmost", True)

    def on_quit(icon, item):
        logger.info("[TRAY] Quit selected — shutting down")
        icon.stop()
        import os
        os._exit(0)  # force full exit

    menu = pystray.Menu(
        pystray.MenuItem("Show Helper", on_show),
        pystray.MenuItem("Quit", on_quit),
    )

    icon = pystray.Icon(
        "Helper",
        create_tray_icon(),
        "Helper — running",
        menu
    )

    thread = threading.Thread(target=icon.run, daemon=True)
    thread.start()
    logger.info("[TRAY] System tray icon started")
    return icon