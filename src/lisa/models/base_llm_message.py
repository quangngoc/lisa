from pydantic import BaseModel


class BaseLLMMessage(BaseModel):
    system_prompt: str | None = None
