"""Structured Outputsで取得したJSON形式のレスポンスのフォーマット"""

from pydantic import BaseModel, Field


class AnswerFormat(BaseModel):
    """
    Structured Outputsで取得した正解の選択肢・正解/不正解の理由のフォーマット
    """

    correct_indexes: list[int] = Field(
        ..., description="正解の選択肢のインデックス(1から始まる)のリスト"
    )
    explanations: list[str] = Field(..., description="正解/不正解の理由のリスト")
