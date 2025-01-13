from pydantic import field_validator

from lisa.models.base_chat_message import BaseChatMessage
from lisa.models.chat_role import ChatRole
from lisa.models.tool_call_response import ToolCallResponse


class AssistantChatMessage(BaseChatMessage):
    role: ChatRole = ChatRole.ASSISTANT
    tool_calls: list[ToolCallResponse] | None = None

    @field_validator("role")
    @classmethod
    def role_is_assistant(cls, v):
        if v is not ChatRole.ASSISTANT:
            raise ValueError(f"{AssistantChatMessage.__name__} must have role = 'assistant'")
        return v
