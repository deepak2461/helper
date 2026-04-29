
from openai import OpenAI
import os
from logger import logger


SYSTEM_PROMPT_TEMPLATE = """You are helping someone answer interview questions in real time during a live job interview.

Here is their resume:
{resume}

Here is the job description they are interviewing for:
{jd}

Your job:
- Answer the interview question as if YOU are the candidate speaking
- Sound like a real human — natural, conversational, confident
- Use relevant keywords from the resume and job description naturally — don't force them
- Match answer length to the question — short questions get short answers, complex ones get fuller answers
- Use STAR format (Situation, Task, Action, Result) only when the question is behavioral (e.g. "tell me about a time...")
- Never sound like an AI — no bullet points, no "Certainly!", no "Great question!", no corporate speak
- Never start with "I" as the very first word — vary your sentence starts
- Speak in first person always
- If you don't have enough context from the resume, give a honest, grounded human answer anyway
"""


class AnswerEngine:
    def __init__(self, resume: str, jd: str):
        #self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.client = OpenAI(api_key=os.getenv("GROQ_API_KEY") , base_url="https://api.groq.com/openai/v1")
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            resume=resume if resume else "Not provided",
            jd=jd if jd else "Not provided"
        )
        logger.info("[LLM] Answer engine initialized")

    def generate(self, question: str) -> str:
        """Generate a human-like answer for the given interview question."""
        logger.info(f"[LLM] Generating answer for: '{question}'")
        print("\n💡 ", end="", flush=True)
        full_answer = ""


        try:
            response = self.client.chat.completions.create(
                #model="gpt-4o-mini",
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.85,      # slightly creative = more human
                max_tokens=500,
                presence_penalty=0.3,  # avoid repetition
                stream=True, 
            )
            
            ## Use this for OpenAI streaming
            # for chunk in stream:
            #     delta = chunk.choices[0].delta.content
            #     if delta:
            #         print(delta, end="", flush=True)
            #         full_answer += delta

            ## Use this for Groq streaming
            for chunk in response:
                # Groq sometimes returns chunks with no choices
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta is not None:
                    print(delta, end="", flush=True)
                    full_answer += delta

            print("\n")
            logger.info(f"[LLM] Answer generated ({len(full_answer)} chars)")
            return full_answer

            # answer = response.choices[0].message.content.strip()
            # logger.info(f"[LLM] Answer generated ({len(answer)} chars)")
            # return answer

        except Exception as e:
            logger.error(f"[LLM] Error generating answer: {e}")
            return ""