from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SearchOutput(BaseModel):
    file_name: str = Field(description="The file name")
    content: str = Field(description="The content of the file")

    @classmethod
    def from_hit(cls, hit: dict) -> "SearchOutput":
        return cls(
            file_name=hit["_source"]["file_name"], content=hit["_source"]["content"]
        )


class DataSource(str, Enum):
    ACCOUNT = "account"
    PROJECT = "project"
    REPORT = "report"
    SYSTEM = "system"


class QuestionAnalysis(BaseModel):
    keywords: list[str] = Field(
        ...,
        description="ユーザーの質問から抽出した検索用キーワードのリスト",
    )
    data_source: Literal["account", "project", "report", "system"] = Field(
        ...,
        description="質問のドメインに基づくデータソース",
    )


class FilteredData(BaseModel):
    relevant_entries: list[str] = Field(
        ...,
        description="質問への回答に必要な情報のリスト",
    )


class WorkflowResult(BaseModel):
    question: str = Field(..., description="ユーザーの元の質問")
    analysis: QuestionAnalysis = Field(..., description="質問分析の結果")
    search_results: list[SearchOutput] = Field(..., description="検索結果")
    filtered_data: list[str] = Field(..., description="絞り込まれたデータ")
    answer: str = Field(..., description="最終的な回答")
