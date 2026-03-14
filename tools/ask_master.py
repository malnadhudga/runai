import os

from dotenv import load_dotenv

load_dotenv()

from crew.core.llm_client import LLMClient
from crew.core.prompts import ASK_MASTER_SYSTEM_PROMPT


def ask_master(question: str) -> str:
    """Escalate a question to the master supervisor and return the answer.

    Args:
        question: A specific technical question from a blocked slave agent.

    Returns:
        The supervisor's text response, or an error string on failure.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in .env file")

    llm_client = LLMClient(provider="gemini", model="gemma-3-1b-it", api_key=api_key)
    messages = [{"role": "user", "content": question}]

    try:
        return llm_client.chat(messages, system=ASK_MASTER_SYSTEM_PROMPT)
    except Exception as e:
        return f"error: {e}"
