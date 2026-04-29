# ============================================================
# LLM / ANSWER_ENGINE.PY
# Generates streaming answers using Groq (or OpenAI)
# Streams tokens to terminal + WebSocket clients
# ============================================================

from openai import OpenAI
import os
from logger import logger


SYSTEM_PROMPT_TEMPLATE = """You are helping someone answer interview questions in real time during a live job interview.

Here is their resume:
{resume}

Here is the job description they are interviewing for:
{jd}

Your job:
- Answer as if YOU are the candidate speaking out loud right now
- Sound like a real human — relaxed, natural, confident, not robotic
- Use keywords from the resume and JD naturally — don't stuff them in
- Match length to the question — short question = short answer, behavioral = fuller answer
- Use STAR format only for behavioral questions ("tell me about a time...")
- For coding questions — give a brief explanation first, then the code, then explain it simply
- Never use bullet points or lists — prose only (except code blocks)
- Never start with filler like "Certainly!", "Great question!", "Of course!"
- Never sound like a chatbot
- Vary your sentence openings — don't always start with "I"
- Speak in first person always
- Be honest and grounded — if context is thin, give a real human answer anyway
"""


class AnswerEngine:
    def __init__(self, resume: str, jd: str):

        # -------- LLM Client (Groq for testing, swap base_url for OpenAI) --------
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            resume=resume if resume else "Not provided",
            jd=jd if jd else "Not provided"
        )
        logger.info("[LLM] Answer engine initialized")

    # -------- Generate Answer (streaming) --------
    def generate(self, question: str) -> str:
        from server.socket_server import send_to_clients

        logger.info(f"[LLM] Generating answer for: '{question}'")
        print("\n💡 ", end="", flush=True)
        full_answer = ""

        # -------- Notify UI: question received --------
        send_to_clients({"type": "question", "text": question})

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.9,
                max_tokens=600,
                presence_penalty=0.4,
                stream=True,
            )

            # -------- Stream tokens to terminal + UI --------
            for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta is not None:
                    print(delta, end="", flush=True)
                    full_answer += delta
                    # -------- Send each token to UI --------
                    send_to_clients({"type": "answer_chunk", "text": delta})

            print("\n")
            # -------- Notify UI: answer complete --------
            send_to_clients({"type": "answer_done", "text": ""})
            logger.info(f"[LLM] Answer complete ({len(full_answer)} chars)")
            return full_answer

        except Exception as e:
            logger.error(f"[LLM] Error generating answer: {e}")
            send_to_clients({"type": "status", "text": "❌ LLM error"})
            return ""

    # -------- Screen Capture: Screenshot → OCR → LLM --------
    def generate_from_screen(self):
        from ui.screen_capture import capture_and_extract
        from server.socket_server import send_to_clients

        logger.info("[LLM] Screen capture triggered")
        send_to_clients({"type": "status", "text": "📸 Analysing screen..."})

        text = capture_and_extract()
        if not text:
            logger.warning("[LLM] No text found on screen")
            send_to_clients({"type": "status", "text": "❌ No text found on screen"})
            return

        logger.info(f"[LLM] Screen text extracted: {text[:100]}...")
        question = f"The interviewer has shown this on screen — solve or explain it:\n\n{text}"
        self.generate(question)