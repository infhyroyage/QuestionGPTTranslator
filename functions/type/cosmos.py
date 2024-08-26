"""Cosmos DB Type Definitions"""

from typing import List, Optional, TypedDict


class Answer(TypedDict):
    """
    Answer Type of Answer Container
    """

    id: str
    questionNumber: int
    correctIdxes: List[int]
    explanations: List[str]
    testId: str


class EscapeTranslatedIdxes(TypedDict, total=False):
    """
    Type of escapeTranslatedIdxes in Question
    """

    subjects: Optional[List[int]]
    choices: Optional[List[int]]


class Question(TypedDict):
    """
    Question Type of Question Container
    """

    id: str
    number: int
    subjects: List[str]
    choices: List[str]
    communityVotes: List[str]
    indicateSubjectImgIdxes: Optional[List[int]]
    indicateChoiceImgs: Optional[List[Optional[str]]]
    escapeTranslatedIdxes: Optional[EscapeTranslatedIdxes]
    testId: str


class Test(TypedDict):
    """
    Item Type of Test Container
    """

    id: str
    courseName: str
    testName: str
    length: int
