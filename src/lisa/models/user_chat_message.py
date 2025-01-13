from typing import Any

from pydantic import field_validator

from lisa.models.base_chat_message import BaseChatMessage
from lisa.models.chat_role import ChatRole


class UserChatMessage(BaseChatMessage):
    role: ChatRole = ChatRole.USER
    content: str | list[dict[str, Any]]

    @field_validator("role")
    @classmethod
    def role_is_user(cls, v):
        if v is not ChatRole.USER:
            raise ValueError(f"{UserChatMessage.__name__} must have role = 'user'")
        return v
