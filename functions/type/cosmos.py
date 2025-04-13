"""Cosmos DBの項目の型定義"""

from typing import List, Optional, TypedDict


class Answer(TypedDict):
    """
    Answerコンテナーの項目の型
    """

    id: str
    questionNumber: int
    correctIdxes: List[int]
    explanations: List[str]
    communityVotes: List[str]
    testId: str


class Progress(TypedDict):
    """
    Progressコンテナーの項目の型
    """

    id: str
    userTestId: str
    questionNumber: int
    isCorrect: bool
    choiceSentences: List[str]
    choiceImgs: List[Optional[str]]
    selectedIdxes: List[int]
    correctIdxes: List[int]


class EscapeTranslatedIdxes(TypedDict, total=False):
    """
    QuestionコンテナーのescapeTranslatedIdxesフィールドの型
    """

    subjects: Optional[List[int]]
    choices: Optional[List[int]]


class Question(TypedDict):
    """
    Questionコンテナーの項目の型
    """

    id: str
    number: int
    subjects: List[str]
    choices: List[str]
    isMultiplied: bool
    communityVotes: List[str]
    indicateSubjectImgIdxes: Optional[List[int]]
    indicateChoiceImgs: Optional[List[Optional[str]]]
    escapeTranslatedIdxes: Optional[EscapeTranslatedIdxes]
    testId: str


class Test(TypedDict):
    """
    Testコンテナーの項目の型
    """

    id: str
    courseName: str
    testName: str
    length: int
