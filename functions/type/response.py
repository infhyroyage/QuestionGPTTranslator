"""
Functions Application Response Type Definitions
"""

from typing import List, Optional, TypedDict


class GetHealthcheckRes(TypedDict):
    """
    [GET] /healthcheck Response Type
    """

    __root__: str


class Subject(TypedDict):
    """
    Type of array element in the subjects array of the response for
    [GET] /tests/{testId}/questions/{questionNumber}
    """

    sentence: str
    isIndicatedImg: bool
    isEscapedTranslation: bool


class Choice(TypedDict):
    """
    Type of array element in the choices array of the response for
    [GET] /tests/{testId}/questions/{questionNumber}
    """

    sentence: str
    img: Optional[str]
    isEscapedTranslation: bool


class GetQuestionRes(TypedDict):
    """
    [GET] /tests/{testId}/questions/{questionNumber} Response Type
    """

    subjects: List[Subject]
    choices: List[Choice]
    isMultiplied: bool


class GetTestRes(TypedDict):
    """
    [GET] /tests/{testId} Response Type
    """

    testName: str
    length: int


class Test(TypedDict):
    """
    Type of array element in the response of [GET] /tests
    """

    id: str
    testName: str


class GetTestsRes(TypedDict):
    """
    [GET] /tests Response Type
    """

    __root__: dict[str, List[Test]]


class PostAnswerRes(TypedDict, total=False):
    """
    [POST] /answer Response Type
    """

    correctIdxes: List[int]
    explanations: List[str]


class PutEn2JaRes(TypedDict):
    """
    [PUT] /en2ja Response Type
    """

    __root__: List[str]
