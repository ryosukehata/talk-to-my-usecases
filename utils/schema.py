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
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Generator, Literal, Optional, Union

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
    GetJsonSchemaHandler,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from typing_extensions import TypedDict


from enum import Enum


class PromptType(str, Enum):
    DECISION = "decision"
    QUESTION = "questions"
    SOLUTION = "solution"


class LLMDeploymentSettings(BaseModel):
    target_feature_name: str = "resultText"
    prompt_feature_name: str = "promptText"


class DataRegistryDataset(BaseModel):
    id: str
    name: str
    created: str
    size: str



class CleansedColumnReport(BaseModel):
    new_column_name: str
    original_column_name: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    original_dtype: str | None = None
    new_dtype: str | None = None
    conversion_type: str | None = None



class DataDictionaryColumn(BaseModel):
    data_type: str
    column: str
    description: str


class DataDictionary(BaseModel):
    name: str
    column_descriptions: list[DataDictionaryColumn]

    @classmethod
    def from_analyst_df(
        cls,
        df: pl.DataFrame,
        name: str = "analysis_result",
        column_descriptions: str = "Analysis result column",
    ) -> "DataDictionary":
        return DataDictionary(
            name=name,
            column_descriptions=[
                DataDictionaryColumn(
                    column=col,
                    description=column_descriptions,
                    data_type=str(df[col].dtype),
                )
                for col in df.columns
            ],
        )

    @classmethod
    def from_application_df(
        cls, df: pl.DataFrame, name: str = "analysis_result"
    ) -> "DataDictionary":
        columns = {"column", "description", "data_type"}
        if not columns.issubset(df.columns):
            raise ValueError(f"DataFrame must contain columns: {columns}")

        column_descriptions = [
            DataDictionaryColumn(
                column=row["column"],
                description=row["description"],
                data_type=row["data_type"],
            )
            for row in df.rows(named=True)
        ]

        return DataDictionary(name=name, column_descriptions=column_descriptions)

    def to_application_df(self) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "column": [c.column for c in self.column_descriptions],
                "description": [c.description for c in self.column_descriptions],
                "data_type": [c.data_type for c in self.column_descriptions],
            }
        )


class DataDictionaryResponse(DataDictionary):
    in_progress: bool = False


class DictionaryGeneration(BaseModel):
    """Validates LLM responses for data dictionary generation

    Attributes:
        columns: List of column names
        descriptions: List of column descriptions

    Raises:
        ValueError: If validation fails
    """

    columns: list[str]
    descriptions: list[str]

    @field_validator("descriptions")
    @classmethod
    def validate_descriptions(cls, v: Any, values: Any) -> Any:
        # Check if columns exists in values
        if "columns" not in values.data:
            raise ValueError("Columns must be provided before descriptions")

        # Check if lengths match
        if len(v) != len(values.data["columns"]):
            raise ValueError(
                f"Number of descriptions ({len(v)}) must match number of columns ({len(values['columns'])})"
            )

        # Validate each description
        for desc in v:
            if not desc or not isinstance(desc, str):
                raise ValueError("Each description must be a non-empty string")
            if len(desc.strip()) < 10:
                raise ValueError("Descriptions must be at least 10 characters long")

        return v

    @field_validator("columns")
    @classmethod
    def validate_columns(cls, v: Any) -> Any:
        if not v:
            raise ValueError("Columns list cannot be empty")

        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate column names are not allowed")

        # Validate each column name
        for col in v:
            if not col or not isinstance(col, str):
                raise ValueError("Each column name must be a non-empty string")

        return v

    def to_dict(self) -> dict[str, str]:
        """Convert columns and descriptions to dictionary format

        Returns:
            Dict mapping column names to their descriptions
        """
        return dict(zip(self.columns, self.descriptions))


@dataclass
class RunAnalysisRequest:
    dataset_names: list[str]
    question: str



class RunAnalysisResultMetadata(BaseModel):
    duration: float
    attempts: int
    datasets_analyzed: int | None = None
    total_rows_analyzed: int | None = None
    total_columns_analyzed: int | None = None
    exception: AnalysisError | None = None


class AnalysisError(BaseModel):
    exception_history: list[CodeExecutionError] | None = None

    @classmethod
    def from_value_error(
        cls,
        exception: ValueError,
    ) -> "AnalysisError":
        return AnalysisError(
            exception_history=[
                CodeExecutionError(
                    exception_str=str(exception),
                    traceback_str=None,
                    code=None,
                    stdout=str(exception),
                    stderr=str(exception),
                )
            ],
        )


class CodeExecutionError(BaseModel):
    code: str | None = None
    exception_str: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    traceback_str: str | None = None




class GetBusinessAnalysisMetadata(BaseModel):
    duration: float | None = None
    question: str | None = None
    rows_analyzed: int | None = None
    columns_analyzed: int | None = None
    exception_str: str | None = None


class BusinessAnalysisGeneration(BaseModel):
    bottom_line: str
    additional_insights: str
    follow_up_questions: list[str]



class ChatRequest(BaseModel):
    """Request model for chat history processing

    Attributes:
        messages: list of dictionaries containing chat messages
                 Each message must have 'role' and 'content' fields
                 Role must be one of: 'user', 'assistant', 'system'
    """

    messages: list[ChatCompletionMessageParam] = Field(min_length=1)


class QuestionListGeneration(BaseModel):
    questions: list[str]


class ValidatedQuestion(BaseModel):
    """Stores validation results for suggested questions"""

    question: str


class RunDatabaseAnalysisRequest(BaseModel):
    type: Literal["database"] = "database"
    dataset_names: list[str]
    question: str = Field(min_length=1)


class DatabaseAnalysisCodeGeneration(BaseModel):
    code: str
    description: str


class EnhancedQuestionGeneration(BaseModel):
    enhanced_user_message: str


class CodeGeneration(BaseModel):
    code: str
    description: str


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
    EnhancedQuestionGeneration,
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
