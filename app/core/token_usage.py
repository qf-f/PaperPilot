from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


_usage_var: ContextVar[TokenUsage | None] = ContextVar("paper_pilot_token_usage", default=None)


def start_token_usage() -> object:
    return _usage_var.set(TokenUsage())


def add_token_usage(prompt_tokens: int, completion_tokens: int, total_tokens: int, estimated_cost: float) -> None:
    usage = _usage_var.get()
    if usage is None:
        return
    usage.prompt_tokens += prompt_tokens
    usage.completion_tokens += completion_tokens
    usage.total_tokens += total_tokens
    usage.estimated_cost += estimated_cost


def get_token_usage() -> TokenUsage:
    return _usage_var.get() or TokenUsage()


def reset_token_usage(token: object) -> None:
    _usage_var.reset(token)
