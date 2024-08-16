"""Cosmos DB Type Definitions"""

from typing import List, Optional, TypedDict


class EscapeTranslatedIdxes(TypedDict, total=False):
    """
    Type of escapeTranslatedIdxes in Question
    """

    subjects: Optional[List[int]]
    choices: Optional[List[int]]


class Question(TypedDict):
    """
    Question Type of Test Container
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
