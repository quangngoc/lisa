from pydantic import BaseModel


class ToolCallConfig(BaseModel):
    arguments: str
    name: str
