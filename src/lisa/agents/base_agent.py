import time
from datetime import datetime, timezone

from litellm import acompletion, completion_cost
from litellm.utils import CustomStreamWrapper, ModelResponse

from lisa.exceptions.token_limit_error import TokenLimitError
from lisa.models.base_agent_usage import BaseAgentUsage
from lisa.models.llm_config import LLMConfig


class BaseAgent:
    def __init__(self, llm_config: LLMConfig) -> None:
        self.llm_config = llm_config
        self.agent_usage = BaseAgentUsage()
        self._stats = {
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "tokens_total": 0,
            "total_cost": 0,
            "request_llm": 0,
            "tokens_cached": 0,
        }

    def _fit_messages_within_context(self, messages: list) -> list:
        total_messages_tokens = 0
        trimmed_messages = []
        for message in reversed(messages):
            if "content" not in message:
                trimmed_messages.append(message)
                continue
            total_messages_tokens += self.llm_config.token_counter(messages=[message])
            if total_messages_tokens <= self.llm_config.max_prompt_tokens:
                trimmed_messages.append(message)
            else:
                break

        if not trimmed_messages:
            raise TokenLimitError(
                "The list of input messages became empty after trimming to fit into the model's context window",
                prompt_tokens_count=total_messages_tokens,
                exceeded_tokens_count=self.llm_config.max_prompt_tokens - total_messages_tokens,
            )

        if trimmed_messages[-1]["role"] == "assistant":
            trimmed_messages.pop()
        return list(reversed(trimmed_messages))

    def _update_usage(
        self,
        model_response: ModelResponse | CustomStreamWrapper,
        start_time: float,
        end_time: float,
        messages: list,
    ):
        llm_duration = (end_time - start_time) * 1000
        llm_call = {
            "start_time": datetime.fromtimestamp(start_time, tz=timezone.utc),
            "end_time": datetime.fromtimestamp(end_time, tz=timezone.utc),
            "request_llm": llm_duration,
        }
        if isinstance(model_response, ModelResponse):
            llm_call["tokens_prompt"] = model_response.usage.prompt_tokens
            llm_call["tokens_completion"] = model_response.usage.completion_tokens
            llm_call["tokens_total"] = model_response.usage.total_tokens
            llm_call["total_cost"] = completion_cost(model_response)
            if model_response.usage.prompt_tokens_details:
                llm_call["tokens_cached"] = model_response.usage.prompt_tokens_details.cached_tokens
            else:
                # For LLM models from Azure and Google, the prompt_tokens_details is None
                llm_call["tokens_cached"] = 0
        else:
            llm_call["tokens_prompt"] = self.llm_config.token_counter(messages=messages)
        self.agent_usage.llm_calls.append(llm_call)

    async def acompletion(
        self,
        messages: list,
        **kwargs,
    ) -> ModelResponse | CustomStreamWrapper:
        if self.llm_config.context_window and self.llm_config.max_tokens:
            messages = self._fit_messages_within_context(messages)
        max_tokens = kwargs.pop("max_tokens", self.llm_config.max_tokens)

        if "stream_options" in kwargs and self.llm_config.llm_provider == "azure":
            kwargs.pop("stream_options")

        start_time = time.time()
        model_response = await acompletion(
            model=self.llm_config.model,
            base_url=self.llm_config.base_url,
            api_key=self.llm_config.api_key,
            api_version=self.llm_config.api_version,
            max_tokens=max_tokens,
            messages=messages,
            extra_headers={"Connection": "close"},
            **kwargs,
        )
        self._update_usage(model_response=model_response, start_time=start_time, end_time=time.time(), messages=messages)
        return model_response
