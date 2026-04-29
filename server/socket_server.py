# ============================================================
# SERVER / SOCKET_SERVER.PY
# FastAPI + WebSocket server
# Serves both desktop webview and phone browser UI
# ============================================================

import asyncio
import queue
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
from logger import logger

app = FastAPI()

# -------- Connected Clients List --------
connected_clients: list[WebSocket] = []

# -------- Shared state for tkinter polling --------
latest_answer = ""
answer_queue = queue.Queue()

# -------- Serve Main UI Page --------
@app.get("/")
async def get():
    with open("server/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


# -------- WebSocket Endpoint --------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"[WS] Client connected. Total: {len(connected_clients)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        logger.info(f"[WS] Client disconnected. Total: {len(connected_clients)}")


# -------- Global refs (set by main.py) --------
stt = None
engine = None


# -------- Handle Commands from UI --------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"[WS] Client connected. Total: {len(connected_clients)}")
    try:
        while True:
            data = await websocket.receive_json()
            cmd = data.get("cmd")

            # -------- Mode Switch --------
            if cmd == "set_mode":
                manual = data.get("manual", False)
                if stt:
                    stt.set_mode(manual)

            # -------- Manual Start --------
            elif cmd == "manual_start":
                if stt:
                    stt.start_manual()
                    await broadcast({"type": "status", "text": "🎙️ Listening..."})

            # -------- Manual Stop --------
            elif cmd == "manual_stop":
                if stt:
                    stt.stop_manual()
                    await broadcast({"type": "status", "text": "⏹️ Processing..."})

            # -------- Screen Capture --------
            elif cmd == "capture_screen":
                if engine:
                    threading.Thread(
                        target=engine.generate_from_screen,
                        daemon=True
                    ).start()

    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)



# -------- Broadcast to All Clients --------
async def broadcast(message: dict):
    global latest_answer
    # -------- Track latest answer for desktop window polling --------
    if message.get("type") == "answer_chunk":
        latest_answer += message.get("text", "")
        answer_queue.put(("chunk", message.get("text", "")))
    elif message.get("type") == "question":
        latest_answer = ""
        answer_queue.put(("question", message.get("text", "")))
    elif message.get("type") == "answer_done":
        answer_queue.put(("done", ""))
    

    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)
    for c in disconnected:
        if c in connected_clients:
            connected_clients.remove(c)


# -------- Thread-safe Broadcast --------
def send_to_clients(message: dict):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast(message), loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(broadcast(message))
    except Exception as e:
        logger.error(f"[WS] Broadcast error: {e}")


# -------- Start Server in Background Thread --------
def start_server():
    logger.info("[WS] Starting WebSocket server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")


def start_server_thread():
    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()
    logger.info("[WS] Server thread started")