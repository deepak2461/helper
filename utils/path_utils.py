import os
import sys


def resource_path(*parts):
    """
    Files bundled inside PyInstaller
    Example:
        server/static/index.html
        icons/icon.png
    """

    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(".")

    return os.path.join(base, *parts)


def user_path(*parts):
    """
    Files beside the EXE
    Example:
        docs/
        logs/
    """

    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(".")

    return os.path.join(base, *parts)