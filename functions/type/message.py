"""キューストレージのメッセージの型定義"""

from typing import List, TypedDict


class MessageAnswer(TypedDict):
    """
    Answerコンテナーの項目用のメッセージの型
    """

    testId: str
    questionNumber: int
    subjects: List[str]
    choices: List[str]
    correctIdxes: List[int]
    explanations: List[str]
    communityVotes: List[str]
