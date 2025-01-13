import functools
from typing import Callable

from litellm import cost_per_token
from litellm.utils import get_llm_provider, supports_vision, token_counter
from pydantic import BaseModel, ConfigDict, model_validator


class LLMConfig(BaseModel):
    """Configuration for an LLM model."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    model: str
    """The name of the LLM endpoint. Example: 'azure/gpt-4o-mini'"""
    base_url: str | None = None
    api_key: str | None = None
    api_version: str | None = None
    context_window: int | None = None
    """The model context window"""
    max_tokens: int | None = None
    """The maximum number of tokens in the generated completion"""

    @functools.cached_property
    def token_counter(self) -> Callable[[str], int]:
        """Returns a token counter function for the configured LLM."""
        return functools.partial(token_counter, model=self.model)

    @functools.cached_property
    def token_cost_calculator(self) -> Callable[[int, bool], float]:
        """Returns a cost calculator function for the configured LLM."""
        return functools.partial(cost_per_token, model=self.model)

    @functools.cached_property
    def has_vision(self) -> bool:
        """Indicates if the model has vision capabilities."""
        if self.model in ["o1-preview", "o1-mini"]:
            return False
        return supports_vision(model=self.model)

    @functools.cached_property
    def max_prompt_tokens(self) -> int:
        """Calculates the maximum number of tokens allowed for the prompt."""
        # 10% is the margin for max tokens prompt
        return int((self.context_window - self.max_tokens) * 0.9)

    @model_validator(mode="after")
    def validate_api_or_base_url(self) -> "LLMConfig":
        """Validates that at least one of api_key or base_url is provided."""
        if self.api_key is None and self.base_url is None:
            raise ValueError("At least one of api_key or base_url should not be None")
        return self

    @functools.cached_property
    def provider(self) -> str:
        """Returns the provider of the LLM."""
        _, llm_provider, _, _ = get_llm_provider(self.model, api_base=self.base_url)
        return llm_provider
