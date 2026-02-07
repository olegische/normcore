"""
Internal OpenAI-mapped message models and speech acts.
"""

from __future__ import annotations

from typing import Optional, Union
from typing_extensions import Literal

from pydantic import BaseModel, Field


class TextSpeechAct(BaseModel):
    text: str


class RefusalSpeechAct(BaseModel):
    refusal: str


AssistantSpeechAct = Union[TextSpeechAct, RefusalSpeechAct]


class ToolResultSpeechAct(BaseModel):
    tool_name: str
    tool_call_id: Optional[str] = None
    arguments: dict = Field(default_factory=dict)
    result_text: str


class _TextPart(BaseModel):
    type: Literal["text"]
    text: str

    model_config = {
        "extra": "forbid",
    }


class _RefusalPart(BaseModel):
    type: Literal["refusal"]
    refusal: str

    model_config = {
        "extra": "forbid",
    }


_ContentPart = Union[_TextPart, _RefusalPart]


class _FunctionToolCall(BaseModel):
    id: str
    name: str
    arguments: str


class _CustomToolCall(BaseModel):
    id: str
    name: str
    input_value: str


_ToolCall = Union[_FunctionToolCall, _CustomToolCall]


class _AssistantMessage(BaseModel):
    content: str | list[_ContentPart] | None
    tool_calls: list[_ToolCall] = Field(default_factory=list)


class _ToolMessage(BaseModel):
    tool_call_id: str
    content: str | list[_ContentPart] | None


class _FunctionMessage(BaseModel):
    name: str
    content: str | list[_ContentPart] | None


class _OtherMessage(BaseModel):
    role: str


_MappedMessage = Union[_AssistantMessage, _ToolMessage, _FunctionMessage, _OtherMessage]
