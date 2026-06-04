# ============================================================
# SERVER / SOCKET_SERVER.PY
# FastAPI + WebSocket server
# Single /ws endpoint handles all commands and broadcasting
# ============================================================

import asyncio
import queue
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
from logger import logger

app = FastAPI()

# -------- Connected clients --------
connected_clients: list[WebSocket] = []

# -------- Queue for tkinter polling --------
latest_answer = ""
answer_queue = queue.Queue()

# -------- Global refs set by main.py --------
stt = None
engine = None

# -------- Event loop ref for thread-safe broadcast --------
_event_loop = None


# -------- Serve UI page --------
@app.get("/")
async def get():
    with open("server/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


# -------- Single WebSocket endpoint --------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global _event_loop
    _event_loop = asyncio.get_event_loop()

    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"[WS] Client connected. Total: {len(connected_clients)}")

    try:
        while True:
            data = await websocket.receive_json()
            cmd = data.get("cmd")

            # -------- Mode switch --------
            if cmd == "set_mode":
                manual = data.get("manual", False)
                if stt:
                    stt.set_mode(manual)
                # -------- Sync all other clients --------
                await broadcast({"type": "mode_change", "manual": manual})

            # -------- Manual start --------
            elif cmd == "manual_start":
                if stt:
                    stt.start_manual()
                await broadcast({"type": "status", "text": "🎙️ Listening..."})

            # -------- Manual stop --------
            elif cmd == "manual_stop":
                if stt:
                    stt.stop_manual()
                await broadcast({"type": "status", "text": "⏳ Processing..."})

            # -------- Screen capture --------
            elif cmd == "capture_screen":
                if engine:
                    threading.Thread(
                        target=engine.generate_from_screen,
                        daemon=True
                    ).start()

            # -------- Direct ask from input box --------
            elif cmd == "direct_ask":
                text = data.get("text", "").strip()
                if text and engine:
                    threading.Thread(
                        target=engine.generate,
                        args=(text,),
                        daemon=True
                    ).start()
            
            # -------- Timer reset (user clicked timer button to extend timeout) --------
            elif cmd == "reset_timer":
                if stt:
                    stt.extend_timeout()
                await broadcast({"type": "timer_reset"})

            # -------- STT reconnect after Deepgram timeout --------
            elif cmd == "reconnect_stt":
                if stt:
                    stt.reconnect()

    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info(f"[WS] Client disconnected. Total: {len(connected_clients)}")
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# -------- Broadcast to all clients --------
async def broadcast(message: dict):
    global latest_answer

    # -------- Update tkinter queue --------
    msg_type = message.get("type")
    if msg_type == "answer_chunk":
        latest_answer += message.get("text", "")
        answer_queue.put(("chunk", message.get("text", "")))
    elif msg_type == "question":
        latest_answer = ""
        answer_queue.put(("question", message.get("text", "")))
    elif msg_type == "answer_done":
        answer_queue.put(("done", ""))
    elif msg_type == "status":
        answer_queue.put(("status", message.get("text", "")))
    elif msg_type == "mode_change":
        answer_queue.put(("mode", message.get("manual", False)))
    elif msg_type in (
        "speech_activity",
        "timer_reset",
        "stt_connected",
        "stt_disconnected",
        "stt_reconnecting",
    ):
        answer_queue.put((msg_type, ""))

    # -------- Send to all WebSocket clients --------
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)
    for c in disconnected:
        if c in connected_clients:
            connected_clients.remove(c)


# -------- Thread-safe broadcast from sync code --------
def send_to_clients(message: dict):
    global _event_loop
    try:
        if _event_loop and _event_loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast(message), _event_loop)
        else:
            # fallback — put in queue only
            msg_type = message.get("type")
            if msg_type == "answer_chunk":
                answer_queue.put(("chunk", message.get("text", "")))
            elif msg_type == "question":
                answer_queue.put(("question", message.get("text", "")))
            elif msg_type == "answer_done":
                answer_queue.put(("done", ""))
            elif msg_type == "status":
                answer_queue.put(("status", message.get("text", "")))
            elif msg_type in (
                "speech_activity",
                "timer_reset",
                "stt_connected",
                "stt_disconnected",
                "stt_reconnecting",
            ):
                answer_queue.put((msg_type, ""))
    except Exception as e:
        logger.error(f"[WS] send_to_clients error: {e}")


# -------- Start server --------
def start_server():
    logger.info("[WS] Starting server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")


def start_server_thread():
    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()
    logger.info("[WS] Server thread started")
