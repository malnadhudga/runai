import os

from dotenv import load_dotenv

load_dotenv()

from runai.core.llm_client import DEFAULT_GEMINI_MODEL, LLMClient
from runai.core.prompts import ASK_MASTER_SYSTEM_PROMPT


def ask_master(question: str) -> str:
    """Escalate a question to the master supervisor and return the answer.

    Uses the same ``LLMClient`` rules as the rest of the app: local
    ``GEMINI_API_KEY`` for direct Gemini, or ``RUNAI_GEMINI_PROXY_URL`` when the
    key is unset.

    Args:
        question: A specific technical question from a blocked slave agent.

    Returns:
        The supervisor's text response, or an error string on failure.
    """
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    proxy = (os.getenv("RUNAI_GEMINI_PROXY_URL") or "").strip()
    if not api_key and not proxy:
        return "error: set GEMINI_API_KEY or RUNAI_GEMINI_PROXY_URL for ask_master"

    messages = [{"role": "user", "content": question}]
    try:
        llm_client = LLMClient(
            provider="gemini", model=DEFAULT_GEMINI_MODEL, api_key=api_key
        )
        return llm_client.chat(messages, system=ASK_MASTER_SYSTEM_PROMPT)
    except (ValueError, RuntimeError) as e:
        return f"error: {e}"
    except Exception as e:
        return f"error: ask_master LLM call failed: {e}"
