import asyncio
import json
from functools import partial
from inspect import Parameter, signature
from typing import Any, Callable, Optional, cast

from litellm.types.utils import ChatCompletionMessageToolCall
from openai_function_calling import Function, FunctionDict, FunctionInferrer, JsonSchemaType, ParameterDict


def remove_unwanted_whitespaces(s: str):
    """Remove line breaks and multiple spaces."""
    return " ".join(s.split())


def convert_to_json_schema(self, excluded_params: list[str] | None = None) -> FunctionDict:
    """Convert the function instance to a JSON schema dict.

    Raises:
        ValueError: If a parameter is marked as required, but it not defined.

    Returns:
        A JSON schema representation of the function.

    """
    self.validate()

    if excluded_params is not None:
        for excluded_param in excluded_params:
            if excluded_param not in [p.name for p in self.parameters]:
                raise ValueError(f"Trying to exclude a non-existent parameter: {excluded_param}")

    parameters_dict: dict[str, ParameterDict] = {
        p.name: p.to_json_schema() for p in self.parameters or [] if not (excluded_params and p.name in excluded_params)
    }

    output_dict: FunctionDict = {
        "name": self.name,
        "description": self.description,
        "parameters": {
            "type": JsonSchemaType.OBJECT.value,
            "properties": parameters_dict,
        },
    }

    if self.required_parameters is None or len(self.required_parameters) == 0:
        return output_dict

    required_params = [p for p in self.required_parameters if not (excluded_params and p in excluded_params)]
    if required_params:
        output_dict["parameters"]["required"] = sorted(required_params)

    return output_dict


# Monkeypatch this method to support excluding certain params from the tool's JSON schema
Function.to_json_schema = convert_to_json_schema


def convert_to_openai_tool(
    function: Callable | partial,
    excluded_params: list[str] | None = None,
    strict: Optional[bool] = None,
) -> dict[str, Any]:
    """Convert a Python function to an OpenAI tool-calling API compatible dict.

    Assumes the Python function has type hints and a docstring with a description. If
        the docstring has Google Python style argument descriptions, these will be
        included as well.
    """
    if isinstance(function, partial):
        partial_func = function
        if excluded_params is None:
            excluded_params = []
        f = cast(Callable, partial_func.func)

        if partial_func.args:
            sig = signature(f)
            for param_name, param in sig.parameters.items():
                if param.kind in [Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD]:
                    excluded_params.append(param_name)
                if len(excluded_params) == len(function.args):
                    break

        excluded_params.extend(partial_func.keywords.keys())
    else:
        f = function

    tool_json_schema = FunctionInferrer.infer_from_function_reference(f).to_json_schema(
        excluded_params=excluded_params  # pyright: ignore [reportCallIssue]
    )

    # Remove unwanted line breaks in the parameter description, which can be left by the package docstring_parser
    for param_info in tool_json_schema.get("parameters", {}).get("properties", {}).values():
        if "description" in param_info:
            param_info["description"] = remove_unwanted_whitespaces(param_info["description"])

    if not tool_json_schema["description"].strip():
        del tool_json_schema["description"]
    else:
        tool_json_schema["description"] = remove_unwanted_whitespaces(tool_json_schema["description"])

    return {"type": "function", "function": tool_json_schema}


async def execute_tool(tool_call: ChatCompletionMessageToolCall, tool_dict: dict[str, Callable], **extra_tool_args):
    tool_name = tool_call.function.name
    if tool_name not in tool_dict:
        raise ValueError(f"{tool_name} is not a valid tool name.")

    try:
        if tool_call.function.arguments:
            tool_args = json.loads(tool_call.function.arguments)
        else:
            tool_args = {}
    except json.JSONDecodeError as ex:
        raise ValueError(f"Tool call arguments were provided in an invalid JSON: {ex}") from None

    func_result = tool_dict[tool_name](**(tool_args | extra_tool_args))
    if asyncio.iscoroutine(func_result):
        return await func_result
    else:
        return func_result
