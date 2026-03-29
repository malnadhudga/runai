import os

import requests
from dotenv import load_dotenv

load_dotenv()

import openai
import google.generativeai as genai

# All Gemini calls in this project use this model (Google AI / proxy).
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"


class LLMClient:
    """Unified interface for calling LLM APIs (OpenAI, Gemini).

    Gemini: if ``api_key`` (``GEMINI_API_KEY``) is set, calls Google directly and
    ignores ``RUNAI_GEMINI_PROXY_URL``. If there is no local key but
    ``RUNAI_GEMINI_PROXY_URL`` is set, each call ``POST``s to your proxy (server
    uses the platform key). We do not send the user's key in the proxy payload
    for now.
    """

    def __init__(self, provider: str, model: str, api_key: str) -> None:
        if provider not in ("openai", "gemini"):
            raise ValueError(f"Unknown provider '{provider}'. Use 'openai' or 'gemini'.")
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self._gemini_proxy_url = (os.getenv("RUNAI_GEMINI_PROXY_URL") or "http://35.225.99.206:8080").strip() or None
        self._gemini_proxy_token = (os.getenv("RUNAI_GEMINI_PROXY_TOKEN") or "").strip() or None
        self._proxy_client_id = (os.getenv("RUNAI_PROXY_CLIENT_ID") or "").strip() or None

        if provider == "gemini":
            if not self._gemini_proxy_url and not self.api_key:
                raise ValueError(
                    "Gemini needs RUNAI_GEMINI_PROXY_URL or GEMINI_API_KEY in the environment."
                )

    def chat(self, messages: list[dict], system: str = "") -> str:
        if self.provider == "openai":
            return self._chat_openai(messages, system)
        return self._chat_gemini(messages, system)

    def _chat_openai(self, messages: list[dict], system: str) -> str:
        try:
            # max_retries=0 prevents silent backoff waits on rate-limit/5xx errors
            client = openai.OpenAI(api_key=self.api_key, max_retries=0)
            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)
            response = client.chat.completions.create(
                model=self.model,
                messages=full_messages,
            )
            return response.choices[0].message.content
        except openai.AuthenticationError as e:
            raise RuntimeError(f"OpenAI authentication error (check your API key): {e}") from e
        except openai.BadRequestError as e:
            raise RuntimeError(f"OpenAI bad request (token limit or invalid input): {e}") from e
        except openai.RateLimitError as e:
            raise RuntimeError(f"OpenAI rate limit exceeded: {e}") from e
        except openai.APIStatusError as e:
            raise RuntimeError(f"OpenAI API error {e.status_code}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}") from e

    def _chat_gemini(self, messages: list[dict], system: str) -> str:
        if self.api_key:
            return self._chat_gemini_direct(messages, system)
        if self._gemini_proxy_url:
            return self._chat_gemini_via_proxy(messages, system)
        raise RuntimeError("Gemini: set GEMINI_API_KEY or RUNAI_GEMINI_PROXY_URL.")

    def _chat_gemini_direct(self, messages: list[dict], system: str) -> str:
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)

            prompt_parts = []
            if system:
                prompt_parts.append(f"[System]\n{system}\n")
            for msg in messages:
                role = msg["role"].capitalize()
                prompt_parts.append(f"[{role}]\n{msg['content']}")
            prompt = "\n\n".join(prompt_parts)

            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini API call failed: {e}") from e

    def _chat_gemini_via_proxy(self, messages: list[dict], system: str) -> str:
        if not self._gemini_proxy_url:
            raise RuntimeError("RUNAI_GEMINI_PROXY_URL is not set.")

        payload: dict = {
            "model": self.model,
            "system": system,
            "messages": messages,
        }
        if self._proxy_client_id:
            payload["client_id"] = self._proxy_client_id

        headers = {"Content-Type": "application/json"}
        if self._gemini_proxy_token:
            headers["Authorization"] = f"Bearer {self._gemini_proxy_token}"
        if self._proxy_client_id:
            headers["X-Runai-Client-Id"] = self._proxy_client_id

        try:
            response = requests.post(
                self._gemini_proxy_url,
                json=payload,
                headers=headers,
                timeout=60,
            )
        except requests.Timeout as e:
            raise RuntimeError("Gemini proxy timed out after 60s.") from e
        except requests.RequestException as e:
            raise RuntimeError(f"Gemini proxy request failed: {e}") from e

        if response.status_code == 401:
            raise RuntimeError("Gemini proxy: authentication failed (check RUNAI_GEMINI_PROXY_TOKEN).")
        if response.status_code == 429:
            raise RuntimeError("Gemini proxy: rate limit exceeded.")
        if response.status_code == 400:
            raise RuntimeError(f"Gemini proxy: bad request (token limit or invalid input): {response.text[:200]}")
        if response.status_code >= 500:
            raise RuntimeError(f"Gemini proxy: server error {response.status_code}: {response.text[:200]}")
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise RuntimeError(f"Gemini proxy HTTP error: {e}") from e

        try:
            data = response.json()
        except ValueError:
            text = (response.text or "").strip()
            if not text:
                raise RuntimeError("Gemini proxy returned an empty response.") from None
            return text

        for key in ("text", "content", "message", "response"):
            if key in data and isinstance(data[key], str) and data[key].strip():
                return data[key]
        raise RuntimeError(
            f"Gemini proxy JSON missing a string text field (got keys: {list(data.keys())})."
        )
