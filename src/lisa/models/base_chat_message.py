from pydantic import BaseModel

from lisa.models.chat_role import ChatRole


class BaseChatMessage(BaseModel):
    content: str | None = None
    role: ChatRole
