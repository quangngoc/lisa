from pydantic import field_validator

from lisa.models.base_chat_message import BaseChatMessage
from lisa.models.chat_role import ChatRole


class SystemChatMessage(BaseChatMessage):
    role: ChatRole = ChatRole.SYSTEM

    @field_validator("role")
    @classmethod
    def role_is_system(cls, v):
        if v is not ChatRole.SYSTEM:
            raise ValueError(f"{SystemChatMessage.__name__} must have role = 'system'")
        return v
