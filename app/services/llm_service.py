from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.rate_limit import RateLimitError, check_llm_rate_limit
from app.core.token_usage import add_token_usage


class LLMServiceError(Exception):
    pass


@dataclass
class LLMResult:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.openai_api_key:
            raise LLMServiceError("OPENAI_API_KEY is not configured")

        self.client = OpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            timeout=self.settings.openai_timeout_seconds,
        )

    def generate(self, system_prompt: str, user_prompt: str, user_id: str | None = None) -> str:
        return self.generate_with_usage(system_prompt, user_prompt, user_id=user_id).content

    def generate_with_usage(self, system_prompt: str, user_prompt: str, user_id: str | None = None) -> LLMResult:
        if not user_prompt.strip():
            raise LLMServiceError("User prompt cannot be empty")
        try:
            check_llm_rate_limit(user_id)
        except RateLimitError as exc:
            raise LLMServiceError(str(exc)) from exc
        return self._request_chat_completion(system_prompt, user_prompt)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _request_chat_completion(self, system_prompt: str, user_prompt: str) -> LLMResult:
        try:
            response = self.client.chat.completions.create(
                model=self.settings.chat_model,
                temperature=self.settings.chat_temperature,
                max_tokens=self.settings.chat_max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content if response.choices else None
            if not content or not content.strip():
                raise LLMServiceError("LLM returned empty content")
            usage = response.usage
            prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
            total_tokens = int(getattr(usage, "total_tokens", 0) or prompt_tokens + completion_tokens)
            estimated_cost = (
                prompt_tokens / 1000 * self.settings.llm_prompt_cost_per_1k
                + completion_tokens / 1000 * self.settings.llm_completion_cost_per_1k
            )
            add_token_usage(prompt_tokens, completion_tokens, total_tokens, estimated_cost)
            return LLMResult(
                content=content.strip(),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost,
            )
        except LLMServiceError:
            raise
        except Exception as exc:
            raise LLMServiceError(f"LLM API call failed: {exc}") from exc
