from typing import Any

from pydantic import BaseModel


class BaseAgentUsage(BaseModel):
    llm_calls: list[dict[str, Any]] | None = []
    llm_retries_count: int = 0
