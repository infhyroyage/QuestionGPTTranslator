"""Queue Message Type Definitions"""

from typing import List, TypedDict


class MessageAnswer(TypedDict):
    """
    Message Type for Answer Item
    """

    questionNumber: int
    correctIdxes: List[int]
    explanations: List[str]
    testId: str
