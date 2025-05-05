"""キューストレージのメッセージの型定義"""

from typing import List, TypedDict


class MessageAnswer(TypedDict):
    """
    Answerコンテナーの項目用のメッセージの型
    """

    testId: str
    """
    テストID
    """

    questionNumber: int
    """
    問題番号
    """

    subjects: List[str]
    """
    各問題文
    """

    choices: List[str | None]
    """
    各選択肢の文(画像URLのみの場合はNone)
    """

    correctIdxes: List[int]
    """
    正解の選択肢のインデックス
    """

    explanations: List[str]
    """
    各選択肢の正解/不正解の理由
    """

    communityVotes: List[str]
    """
    コミュニティ回答割合
    """
