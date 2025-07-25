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

    answerNum: int
    """
    回答の選択肢の個数
    """

    correctIdxes: List[int]
    """
    正解の選択肢のインデックス
    """

    explanations: List[str]
    """
    各選択肢の正解/不正解の理由
    """


class MessageCommunity(TypedDict):
    """
    Communityコンテナーの項目用のメッセージの型
    """

    questionNumber: int
    """
    問題番号
    """

    testId: str
    """
    テストID
    """

    discussionsSummary: str
    """
    コミュニティでのディスカッションの要約
    """

    votes: List[str]
    """
    コミュニティでの回答の割合
    """
