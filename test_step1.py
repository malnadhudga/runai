import os

from dotenv import load_dotenv

load_dotenv()

from crew.core.llm_client import LLMClient

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found in .env file")

client = LLMClient(provider="openai", model="gpt-4o-mini", api_key=api_key)
response = client.chat([{"role": "user", "content": "say the word HELLO only"}])
print(f"Response: {response!r}")
assert "HELLO" in response, f"Expected 'HELLO' in response, got: {response!r}"
print("Step 1 PASSED")
