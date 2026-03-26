"""Shared Anthropic model configuration helpers."""

from __future__ import annotations

import logging
import os
from typing import Any, Iterable, List

from anthropic import NotFoundError

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = "claude-3-5-haiku-latest"
DEFAULT_ANTHROPIC_FALLBACK_MODELS = (
    "claude-3-5-haiku-latest",
    "claude-3-7-sonnet-latest",
)


def get_anthropic_model() -> str:
    return os.getenv("ANTHROPIC_MODEL", "").strip() or DEFAULT_ANTHROPIC_MODEL


def get_anthropic_fallback_models() -> List[str]:
    raw_value = os.getenv("ANTHROPIC_FALLBACK_MODELS", "").strip()
    if not raw_value:
        return list(DEFAULT_ANTHROPIC_FALLBACK_MODELS)

    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _unique_models(primary_model: str, fallback_models: Iterable[str]) -> List[str]:
    ordered_models: List[str] = []

    for model_name in [primary_model, *fallback_models]:
        if model_name and model_name not in ordered_models:
            ordered_models.append(model_name)

    return ordered_models


def create_message_with_model_fallback(client: Any, **kwargs: Any) -> Any:
    primary_model = kwargs.pop("model", None) or get_anthropic_model()
    candidate_models = _unique_models(primary_model, get_anthropic_fallback_models())

    last_error: Exception | None = None
    for index, model_name in enumerate(candidate_models):
        try:
            if index > 0:
                logger.warning("Retrying Anthropic request with fallback model: %s", model_name)
            return client.messages.create(model=model_name, **kwargs)
        except NotFoundError as exc:
            last_error = exc
            logger.warning("Anthropic model unavailable: %s", model_name)

    if last_error is not None:
        raise last_error

    raise RuntimeError("No Anthropic models configured")