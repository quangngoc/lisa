from typing import Literal

from pydantic import BaseModel

from lisa.models.tool_call_config import ToolCallConfig


class ToolCallResponse(BaseModel):
    function: ToolCallConfig
    id: str
    type: Literal["function"] | None = "function"
