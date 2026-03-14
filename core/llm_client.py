import os

from dotenv import load_dotenv

load_dotenv()

import openai
import google.generativeai as genai


class LLMClient:
    """Unified interface for calling LLM APIs (OpenAI, Gemini)."""

    def __init__(self, provider: str, model: str, api_key: str):
        if provider not in ("openai", "gemini"):
            raise ValueError(f"Unknown provider '{provider}'. Use 'openai' or 'gemini'.")
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def chat(self, messages: list[dict], system: str = "") -> str:
        if self.provider == "openai":
            return self._chat_openai(messages, system)
        return self._chat_gemini(messages, system)

    def _chat_openai(self, messages: list[dict], system: str) -> str:
        try:
            client = openai.OpenAI(api_key=self.api_key)
            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)
            response = client.chat.completions.create(
                model=self.model,
                messages=full_messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}") from e

    def _chat_gemini(self, messages: list[dict], system: str) -> str:
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
