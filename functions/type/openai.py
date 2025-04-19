"""
Azure OpenAIのレスポンスから生成した型定義
"""

from typing import TypedDict


class CorrectAnswers(TypedDict):
    """
    正解の選択肢のインデックス・正解/不正解の理由の型
    """

    correct_indexes: list[int]
    """
    正解の選択肢のインデックス
    """

    explanations: list[str]
    """
    各選択肢の正解/不正解の理由
    """
