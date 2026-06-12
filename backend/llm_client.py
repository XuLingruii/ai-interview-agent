"""DeepSeek API client wrapper. Uses OpenAI-compatible interface.

Features:
  - Automatic .env loading from project root
  - Retry with exponential backoff (3 attempts)
  - Robust JSON extraction from LLM output
"""

import json
import os
import time
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError

# Load .env from project root (parent of backend/)
env_path = Path(__file__).parent.parent / ".env"
loaded = load_dotenv(env_path)
if not loaded:
    print(f"[llm_client] Warning: no .env file found at {env_path}", file=sys.stderr)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # seconds


def get_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            f"DEEPSEEK_API_KEY not set. env_path={env_path}, loaded={loaded}. "
            "Create a .env file in project root or set the environment variable."
        )
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)


def _is_retryable(error: Exception) -> bool:
    return isinstance(error, (APIConnectionError, RateLimitError, APITimeoutError))


def chat(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """Single-turn chat with DeepSeek. Retries on transient errors."""
    client = get_client()
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1 and _is_retryable(e):
                wait = RETRY_BACKOFF[attempt]
                print(f"[llm_client] Retry {attempt + 1}/{MAX_RETRIES} after {wait}s: {e}", file=sys.stderr)
                time.sleep(wait)
            else:
                break

    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts: {last_error}")


def _extract_json(raw: str) -> str:
    """Robust JSON extraction from LLM output. Handles markdown code blocks and stray text."""
    import re
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        return m.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        return raw[start:end + 1]
    if ":" in raw:
        return "{" + raw + "}"
    return raw


def chat_json(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> dict:
    """Chat with DeepSeek and parse the response as JSON. Lower temp for structured output."""
    raw = chat(system_prompt, user_prompt, model=model, temperature=temperature, max_tokens=max_tokens)
    clean = _extract_json(raw)
    try:
        return json.loads(clean)
    except (json.JSONDecodeError, Exception) as e:
        print(f"[chat_json] Parse failed: {e}", file=sys.stderr)
        print(f"[chat_json] Raw response:\n{raw[:800]}", file=sys.stderr)
        print(f"[chat_json] Cleaned:\n{clean[:800]}", file=sys.stderr)
        raise


def truncate_text(text: str, max_chars: int = 3000) -> str:
    """Truncate long user input to avoid exceeding LLM context limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[... 已截断，原文共{len(text)}字符 ...]"
