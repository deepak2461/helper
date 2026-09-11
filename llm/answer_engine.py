# ============================================================
# LLM / ANSWER_ENGINE.PY
# Generates streaming answers using Groq (or OpenAI)
# Streams tokens to terminal + WebSocket clients
# ============================================================

from openai import OpenAI
import os
import threading
from logger import logger


DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"
FALLBACK_LLM_MODEL = "openai/gpt-oss-20b"

# OLD PROMPT
# SYSTEM_PROMPT_TEMPLATE = """You are helping someone answer interview questions in real time during a live job interview.

# Here is their resume:
# {resume}

# Here is the job description they are interviewing for:
# {jd}

# Your job:
# - Answer as if YOU are the candidate speaking out loud right now
# - Sound like a real human — relaxed, natural, confident, not robotic
# - Use keywords from the resume and JD naturally — don't stuff them in
# - Match length to the question — short question = short answer, behavioral = fuller answer
# - Use STAR format only for behavioral questions ("tell me about a time...")
# - For coding questions — give a brief explanation first, then the code, then explain it simply
# - Never use bullet points or lists — prose only (except code blocks)
# - Never start with filler like "Certainly!", "Great question!", "Of course!" , "Sure, let me walk through"
# - Never sound like a chatbot
# - Vary your sentence openings — don't always start with "I"
# - Speak in first person always
# - Be honest and grounded — if context is thin, give a real human answer anyway
# """


SYSTEM_PROMPT_TEMPLATE = """You are helping someone answer interview questions in real time during a live job interview.

Here is their resume:
{resume}

Here is the job description they are interviewing for:
{jd}

Your job:
- Answer as if YOU are the candidate speaking out loud right now.
- Sound like a real human in a live interview: natural, conversational, confident and concise.
- The answer must be something the candidate could comfortably say out loud.
- Never sound like a textbook, documentation, tutorial, blog post, or AI assistant.
- Do not over-explain unless the interviewer explicitly asks for more detail.
- Answer ONLY what the interviewer asked.

IMPORTANT — ANSWER LENGTH:
- Keep answers SHORT by default.
- For a simple definition or conceptual question, answer in 1–3 sentences.
- For a comparison question, give the key difference in 2–4 sentences.
- For a "what is" or "explain" question, give a concise explanation first. Add an example only if it genuinely helps.
- For questions asking for details, explain in more depth, but still avoid unnecessary information.
- If the question can be answered correctly in one sentence, use one sentence.
- NEVER add background information, history, advantages, disadvantages, use cases, or related concepts unless they are relevant to the question.
- NEVER repeat or restate the question.
- Stop answering once the question has been sufficiently answered.

INTERVIEW STYLE:
- Speak naturally, as if talking directly to the interviewer.
- Use simple spoken English rather than formal written English.
- Prefer short sentences.
- Do not use phrases such as "At its core", "Think of it as", "The key takeaway is", "On the other hand", "In practice", "It is worth noting", or similar artificial-sounding transitions unless they are genuinely necessary.
- Do not use unnecessary introductory phrases.
- Do not say "Certainly", "Sure", "Absolutely", "Great question", "Of course", etc.
- Do not use phrases like "If I had to sum it up".
- Do not use rhetorical or storytelling language unless the question is behavioral.
- Vary sentence openings naturally.
- Speak in first person when answering questions about the candidate's experience, but do NOT force first person into technical definitions.

RESUME AND JOB DESCRIPTION:
- Use relevant technologies and keywords from the resume and JD naturally.
- Do not force keywords into the answer.
- Never invent experience, projects, responsibilities, technologies, or achievements that are not supported by the resume.
- If the question asks about something not clearly covered by the resume, give a technically correct concise answer rather than inventing personal experience.

QUESTION TYPES:
- Behavioral questions such as "Tell me about a time..." should use STAR naturally and can be more detailed.
- Technical conceptual questions should normally be concise.
- Comparison questions should focus on the direct difference.
- Definition questions should normally be 1–3 sentences.
- "How does it work?" questions should explain the mechanism briefly.
- Coding questions: give a brief explanation, then the simplest practical code, then a short explanation of the important part.
- Follow-up questions such as "explain that in detail" or "why?" should expand only the previous answer rather than starting an unrelated explanation.

FORMAT:
- Never use bullet points or numbered lists.
- Use prose only, except for code blocks when code is requested.
- Do not use markdown headings.
- Do not add a conclusion or summary unless specifically useful.
- Do not provide multiple alternative answers.

MOST IMPORTANT RULE:
Give the shortest natural answer that completely answers the interviewer's question covering the most important details .
"""


class AnswerEngine:
    def __init__(self, resume: str, jd: str):

        # -------- LLM Client (Groq for testing, swap base_url for OpenAI) --------
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL).strip()
        self.fallback_model = os.getenv("LLM_FALLBACK_MODEL", FALLBACK_LLM_MODEL).strip()
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            resume=resume if resume else "Not provided",
            jd=jd if jd else "Not provided"
        )
        logger.info(
            f"[LLM] Answer engine initialized (model={self.model}, "
            f"fallback={self.fallback_model})"
        )
        # Conversation history for context in follow-up questions
        self.history = []
        # Maximum number of previous Q&A pairs to retain
        self.max_history = 3
        # Flag to indicate screen capture flow
        self.is_screen_capture = False
        self.generation_lock = threading.Lock()
        self.request_number = 0

    def generate(self, question: str, display_text: str | None = None) -> str:
        """Keep streamed answers and conversation history in request order."""
        with self.generation_lock:
            self.request_number += 1
            request_number = self.request_number
            return self._generate(question, display_text, request_number)

    # -------- Generate Answer (streaming) --------
    def _generate(
        self,
        question: str,
        display_text: str | None,
        request_number: int,
    ) -> str:
        from server.socket_server import send_to_clients

        logger.info(f"[LLM] Generating answer {request_number} for: '{question}'")
        print("\n💡 ", end="", flush=True)
        full_answer = ""

        # -------- Notify UI: question received --------
        send_to_clients({"type": "question", "text": display_text or question})

        try:
            # -------- Build messages with a stable snapshot of prior answers --------
            messages = (
                [{"role": "system", "content": self.system_prompt}]
                + list(self.history)
                + [{"role": "user", "content": question}]
            )
            response = self._create_completion(messages, request_number)

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
            logger.info(
                f"[LLM] Answer {request_number} complete ({len(full_answer)} chars)"
            )
            logger.info(f"[LLM] Full answer: {full_answer}")
            # -------- Append to conversation history --------
            if full_answer.strip():
                self.history.extend([
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": full_answer},
                ])
            # Trim history to retain only the last max_history interactions
            if len(self.history) > self.max_history * 2:
                self.history = self.history[-self.max_history * 2:]
            return full_answer

        except Exception as e:
            logger.error(f"[LLM] Error generating answer: {e}")
            send_to_clients({"type": "status", "text": "❌ LLM error"})
            return ""

    def _create_completion(self, messages, request_number):
        request_options = {
            "messages": messages,
            "temperature": 0.9,
            "max_tokens": 600,
            "presence_penalty": 0.4,
            "stream": True,
        }
        try:
            return self.client.chat.completions.create(
                model=self.model,
                **request_options,
            )
        except Exception as error:
            status_code = getattr(error, "status_code", None)
            error_code = getattr(error, "code", None)
            unavailable = status_code == 404 or error_code == "model_not_found"
            if not unavailable or self.fallback_model == self.model:
                raise

            logger.warning(
                f"[LLM] Model '{self.model}' unavailable for request "
                f"{request_number}; retrying with '{self.fallback_model}'"
            )
            self.model = self.fallback_model
            return self.client.chat.completions.create(
                model=self.model,
                **request_options,
            )

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
        return self.generate(question, display_text="screen captured")