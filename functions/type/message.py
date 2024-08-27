"""Queue Message Type Definitions"""

from typing import List, TypedDict


class MessageAnswer(TypedDict):
    """
    Message Type for Answer Item
    """

    testId: str
    questionNumber: int
    subjects: List[str]
    choices: List[str]
    correctIndexes: List[int]
    explanations: List[str]
