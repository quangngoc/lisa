from typing import Annotated, Literal

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    message: str | list
    finish_reason: Annotated[
        Literal["stop", "length", "content_filter"] | None,
        Field(
            description=(
                "The reason the model stopped generating tokens. The convention is the same as that of OpenAI:\n"
                "* `stop`: the model hit a natural stop point or a provided stop sequence\n"
                "* `length`: the maximum number of tokens specified in the request was reached\n"
                "* `content_filter`: content was omitted due to a flag the provider's content filters"
            )
        ),
    ] = None
