from collections.abc import AsyncGenerator
from typing import Callable

import chainlit as cl
from litellm.types.utils import ChatCompletionMessageToolCall, Function
from litellm.utils import CustomStreamWrapper, ModelResponse

from lisa.agents.base_agent import BaseAgent
from lisa.models.llm_config import LLMConfig
from lisa.models.llm_response import LLMResponse
from lisa.utils.function_calling import convert_to_openai_tool, execute_tool


class ToolCallAgent(BaseAgent):
    def __init__(self, llm_config: LLMConfig, messages: list, agent_tools: list[Callable]) -> None:
        super().__init__(llm_config=llm_config)
        self.current_iteration = 0
        self.max_iteration = 5
        self.messages = messages
        self.tool_dict = {f.__name__: f for f in agent_tools}
        self.tools = [convert_to_openai_tool(f) for f in agent_tools]

    async def on_message(self, message: str, **kwargs) -> AsyncGenerator[str]:
        self.current_iteration = 0
        self.messages.append({"role": "user", "content": message})
        return self.call_llm(**kwargs)

    @cl.step(type="tool")
    async def call_tool(self, tool_call: ChatCompletionMessageToolCall):
        current_step = cl.context.current_step
        current_step.name = tool_call.function.name
        current_step.input = tool_call.function.arguments
        function_response = await execute_tool(tool_call, self.tool_dict)
        current_step.output = function_response
        current_step.language = "json"
        self.messages.append(
            {
                "role": "tool",
                "name": tool_call.function.name,
                "content": function_response,
                "tool_call_id": tool_call.id,
            }
        )

    async def call_llm(self, **kwargs) -> AsyncGenerator[str]:
        if not kwargs:
            kwargs = {}
        kwargs["tools"] = self.tools
        model_response = await super().acompletion(self.messages, **kwargs)
        tool_calls: list[ChatCompletionMessageToolCall] = []
        if isinstance(model_response, ModelResponse):
            resp_message = model_response.choices[0].message
            tool_calls = resp_message.tool_calls
            if not tool_calls:
                yield LLMResponse(message=resp_message.content).model_dump_json(exclude_none=True)
        elif isinstance(model_response, CustomStreamWrapper):
            async for chunk in model_response:
                delta = chunk.choices[0].delta if chunk.choices and chunk.choices[0].delta is not None else None
                if delta and delta.content:
                    yield LLMResponse(message=delta.content).model_dump_json(exclude_none=True) + "\n"
                elif delta and delta.tool_calls:
                    tc_chunk_list = delta.tool_calls
                    for tc_chunk in tc_chunk_list:
                        if len(tool_calls) <= tc_chunk.index:
                            tool_call = ChatCompletionMessageToolCall(id="", function=Function(name="", arguments=""))
                            tool_calls.append(tool_call)
                        tc = tool_calls[tc_chunk.index]
                        if tc_chunk.id:
                            tc.id += tc_chunk.id
                        if tc_chunk.function.name:
                            tc.function.name += tc_chunk.function.name
                        if tc_chunk.function.arguments:
                            tc.function.arguments += tc_chunk.function.arguments

        if tool_calls and self.current_iteration < self.max_iteration:
            self.messages.append({"role": "assistant", "tool_calls": tool_calls})
            for tool_call in tool_calls:
                await self.call_tool(tool_call=tool_call)
            self.current_iteration += 1
            async for result in self.call_llm(**kwargs):
                yield result
