# Copyright 2024 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Literal, Optional, Union

import pandas as pd
from openai.types.chat.chat_completion_assistant_message_param import (
    ChatCompletionAssistantMessageParam,
)
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from typing_extensions import TypedDict


class PromptType(str, Enum):
    DECISION = "decision"
    QUESTION = "questions"
    SOLUTION = "solution"


class LLMDeploymentSettings(BaseModel):
    target_feature_name: str = "resultText"
    prompt_feature_name: str = "promptText"


class ChatRequest(BaseModel):
    """Request model for chat history processing

    Attributes:
        messages: list of dictionaries containing chat messages
                 Each message must have 'role' and 'content' fields
                 Role must be one of: 'user', 'assistant', 'system'
    """

    messages: list[ChatCompletionMessageParam] = Field(min_length=1)


RuntimeCredentialType = Literal["llm", "db"]


DatabaseConnectionType = Literal["snowflake", "bigquery", "sap", "no_database"]


class AppInfra(BaseModel):
    llm: str
    database: DatabaseConnectionType


UserRoleType = Literal["assistant", "user", "system"]


class Tool(BaseModel):
    name: str
    signature: str
    docstring: str
    function: Callable[..., Any]

    def __str__(self) -> str:
        return f"function: {self.name}{self.signature}\n{self.docstring}\n\n"


Component = Union[
    str,
]


class AnalystChatMessage(BaseModel):
    role: UserRoleType
    content: str
    components: list[Component]
    in_progress: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chat_id: str | None = None

    def to_openai_message_param(self) -> ChatCompletionMessageParam:
        if self.role == "user":
            return ChatCompletionUserMessageParam(role=self.role, content=self.content)
        elif self.role == "assistant":
            return ChatCompletionAssistantMessageParam(
                role=self.role, content=self.content
            )
        elif self.role == "system":
            return ChatCompletionSystemMessageParam(
                role=self.role, content=self.content
            )


class ChatJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle special types."""

    def default(self, obj: Any) -> Any:
        try:
            if isinstance(obj, pd.Period):
                return str(obj)
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            if hasattr(obj, "dtype"):
                return obj.item()
            if hasattr(obj, "model_dump"):
                data = obj.model_dump()
                if isinstance(obj, AnalystChatMessage) and "created_at" in data:
                    if isinstance(data["created_at"], datetime):
                        data["created_at"] = data["created_at"].isoformat()
                return data
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)
        except TypeError:
            return str(obj)  # Fallback to string representation


class ChatHistory(BaseModel):
    user_id: str
    chat_name: str
    data_source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class FileUploadResponse(TypedDict, total=False):
    filename: Optional[str]
    content_type: Optional[str]
    size: Optional[int]
    dataset_name: Optional[str]
    error: Optional[str]


class ChatResponse(TypedDict):
    id: str
    messages: list[AnalystChatMessage]


class DictionaryCellUpdate(BaseModel):
    rowIndex: int
    field: str
    value: str


class LoadDatabaseRequest(BaseModel):
    table_names: list[str]


class ChatCreate(BaseModel):
    name: str
    data_source: str = ""


class ChatUpdate(BaseModel):
    name: str = ""
    data_source: str = ""


class ChatMessagePayload(BaseModel):
    message: str = ""
    enable_chart_generation: bool = True
    enable_business_insights: bool = True
    data_source: str = "file"


class DownloadedRegistryDataset(BaseModel):
    name: str = ""
    error: Optional[str] = None
