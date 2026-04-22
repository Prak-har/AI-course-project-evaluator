import json
import re
from typing import Any

from openai import APIConnectionError, APIError, AuthenticationError, OpenAI, PermissionDeniedError, RateLimitError

from backend.config import get_settings


settings = get_settings()


def sanitize_provider_message(message: str) -> str:
    cleaned = message.strip()
    if not cleaned:
        return ""

    cleaned = re.sub(r"AIza[0-9A-Za-z\-_]{20,}", "[redacted-api-key]", cleaned)
    cleaned = re.sub(r"sk-[0-9A-Za-z\-_]{10,}", "[redacted-api-key]", cleaned)
    cleaned = re.sub(r"sk-proj-[0-9A-Za-z\-_]{10,}", "[redacted-api-key]", cleaned)
    return cleaned


def extract_provider_message(error: Exception) -> str:
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        nested = body.get("error")
        if isinstance(nested, dict):
            message = nested.get("message")
            if isinstance(message, str):
                return sanitize_provider_message(message)
        message = body.get("message")
        if isinstance(message, str):
            return sanitize_provider_message(message)

    return sanitize_provider_message(str(error))


def describe_provider_error(error: Exception) -> str:
    details = extract_provider_message(error)

    if isinstance(error, AuthenticationError):
        return details or "Gemini authentication failed. Check LLM_API_KEY in .env."
    if isinstance(error, PermissionDeniedError):
        return details or "Gemini rejected the request. Check the configured Gemini model names and API permissions."
    if isinstance(error, RateLimitError):
        message = details.lower()
        if "quota" in message or "insufficient_quota" in message:
            return details or "Gemini quota is unavailable for this API key or project. Check billing, limits, or use a different Gemini key."
        return details or "Gemini rate limits were reached. Wait a moment and try again."
    if isinstance(error, APIConnectionError):
        return details or "Could not reach the Gemini API. Check your internet connection and LLM_API_BASE."
    if isinstance(error, APIError):
        return details or "Gemini API request failed. Verify the configured Gemini base URL and model names."
    return details or "Gemini API request failed. Verify the Gemini API key, base URL, and model names in .env."


class LLMClient:
    def __init__(self) -> None:
        self.client: OpenAI | None = None
        if settings.llm_api_key:
            kwargs: dict[str, Any] = {"api_key": settings.llm_api_key}
            if settings.llm_api_base:
                kwargs["base_url"] = settings.llm_api_base
            self.client = OpenAI(**kwargs)

    @property
    def configured(self) -> bool:
        return self.client is not None

    def refresh(self) -> None:
        self.__init__()

    def _require_client(self) -> OpenAI:
        if not self.client:
            raise RuntimeError("LLM_API_KEY is not configured. Add it to the .env file before evaluating submissions.")
        return self.client

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        client = self._require_client()
        embeddings: list[list[float]] = []
        batch_size = 64

        for index in range(0, len(texts), batch_size):
            batch = texts[index : index + batch_size]
            response = client.embeddings.create(model=settings.llm_embedding_model, input=batch)
            embeddings.extend(item.embedding for item in response.data)

        return embeddings

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
        client = self._require_client()
        response = client.chat.completions.create(
            model=settings.llm_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )

        content = response.choices[0].message.content or ""
        return self._extract_json(content)

    def _extract_json(self, content: str) -> dict:
        cleaned = content.strip()
        cleaned = re.sub(r"^```json", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
            if not match:
                raise ValueError(f"Model response was not valid JSON: {content}")
            return json.loads(match.group(1))


llm_client = LLMClient()
