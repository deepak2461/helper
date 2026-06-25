from pathlib import Path

import requests
import os

from logger import logger
from logger import CURRENT_LOG_FILE

from config import ( TG_BOT_TOKEN, TG_CHAT_ID, DC_WEBHOOK_URL )


def tg_log_logger():

    try:

        if not CURRENT_LOG_FILE:
            logger.error("No log file found.")
            return

        if not os.path.exists(CURRENT_LOG_FILE):
            logger.error(f"Log file missing: {CURRENT_LOG_FILE}")
            return

        url = (
            f"https://api.telegram.org/bot"
            f"{TG_BOT_TOKEN}/sendDocument"
        )

        caption = (
            f"Helper Session Finished\n"
            f"File: {os.path.basename(CURRENT_LOG_FILE)}"
        )

        with open(CURRENT_LOG_FILE, "rb") as file:

            response = requests.post(
                url,
                data={
                    "chat_id": TG_CHAT_ID,
                    "caption": caption
                },
                files={
                    "document": file
                },
                timeout=30
            )

        logger.info(
            f"TG logging status: "
            f"{response.status_code}"
        )

    except Exception as e:
        logger.exception(
            f"Failed to log logfile: {e}"
        )

def dc_log_logger():
    try:

        if not CURRENT_LOG_FILE:
            logger.error(" CURRENT_LOG_FILE is empty")
            return

        if not os.path.exists(CURRENT_LOG_FILE):
            logger.error(
                f" Log file not found: {CURRENT_LOG_FILE}"
            )
            return

        filename = os.path.basename(CURRENT_LOG_FILE)
        filesize_kb = round(
            os.path.getsize(CURRENT_LOG_FILE) / 1024,
            2
        )

        content = (
            f"📄 Helper Session Finished\n"
            f"File: {filename}\n"
            f"Size: {filesize_kb} KB"
        )

        with open(CURRENT_LOG_FILE, "rb") as f:

            response = requests.post(
                DC_WEBHOOK_URL,
                data={
                    "content": content
                },
                files={
                    "file": f
                },
                timeout=30
            )

        if response.status_code in (200, 204):
            #logger.info(" Log uploaded successfully")
            pass
        else:
            logger.error(
                f" log logging failed "
                f"Status={response.status_code} "
                f"Response={response.text}"
            )

    except Exception as e:
        logger.exception(
            f" Failed to log logfile : {e}"
        )



def get_prev_log():

    log_dir = Path("logs")

    log_files = sorted(
        log_dir.glob("run_*.log"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    if len(log_files) < 2:
        return None

    return str(log_files[1])


def log_logger():

    try:

        log_dir = Path("logs")

        log_files = sorted(
            log_dir.glob("run_*.log"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # No previous session log
        if len(log_files) < 2:
            return

        previous_log = log_files[1]

        url = (
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
        )
        caption = (
            f"📄 Prev Helper Session Log\n"
            f"File: {os.path.basename(previous_log)}"
        )

        with open(previous_log, "rb") as file:

            tg_response = requests.post(
                url,
                data={
                    "chat_id": TG_CHAT_ID,
                    "caption": caption
                },
                files={
                    "document": file
                },
                timeout=30
            )
            file.seek(0)    # When you read or write to a file in Python, an internal pointer moves forward through the data. If you try to read from the file again after reaching the end, it will return an empty string because there is nothing left to read
            dc_response = requests.post(
                DC_WEBHOOK_URL,
                data={
                    "content":
                        f"📄 Prev Helper Session Log\n"
                        f"{previous_log.name}"
                },
                files={
                    "file": file
                },
                timeout=30
            )
        
        
        logger.info(
            f"TG logging status: "
            f"{tg_response.status_code}"
            #f"{tg_response.text}"
        )

        logger.info(
            f"DC logging status: "
            f"{dc_response.status_code}"
            #f"{dc_response.text}"
        )



    except Exception as e:
        logger.exception(
            f"Failed to log prev log: {e}"
        )



