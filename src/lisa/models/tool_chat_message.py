from pydantic import field_validator

from lisa.models.base_chat_message import BaseChatMessage
from lisa.models.chat_role import ChatRole


class ToolChatMessage(BaseChatMessage):
    role: ChatRole = ChatRole.TOOL
    tool_call_id: str
    name: str
    content: str

    @field_validator("role")
    @classmethod
    def role_is_tool(cls, v):
        if v is not ChatRole.TOOL:
            raise ValueError(f"{ToolChatMessage.__name__} must have role = 'tool'")
        return v
