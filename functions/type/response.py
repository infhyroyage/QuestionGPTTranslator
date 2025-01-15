"""関数アプリのHTTPトリガーのレスポンスボディの型定義"""

from typing import List, Optional, TypedDict


class GetAnswerRes(TypedDict):
    """
    [GET] /tests/{testId}/answers/{questionNumber} のレスポンスボディの型
    """

    correctIdxes: List[int]
    explanations: List[str]


class GetHealthcheckRes(TypedDict):
    """
    [GET] /healthcheck のレスポンスボディの型
    """

    __root__: str


class Subject(TypedDict):
    """
    [GET] /tests/{testId}/questions/{questionNumber} のレスポンスボディのsubjectsフィールドの各要素の型
    """

    sentence: str
    isIndicatedImg: bool
    isEscapedTranslation: bool


class Choice(TypedDict):
    """
    [GET] /tests/{testId}/questions/{questionNumber} のレスポンスボディのchoicesフィールドの各要素の型
    """

    sentence: str
    img: Optional[str]
    isEscapedTranslation: bool


class GetQuestionRes(TypedDict):
    """
    [GET] /tests/{testId}/questions/{questionNumber} のレスポンスボディの型
    """

    subjects: List[Subject]
    choices: List[Choice]
    isMultiplied: bool


class GetTestRes(TypedDict):
    """
    [GET] /tests/{testId} のレスポンスボディの型
    """

    courseName: str
    testName: str
    length: int


class Test(TypedDict):
    """
    [GET] /tests のレスポンスボディの各要素の型
    """

    id: str
    testName: str


class GetTestsRes(TypedDict):
    """
    [GET] /tests のレスポンスボディの型
    """

    __root__: dict[str, List[Test]]


class PostAnswerRes(TypedDict, total=False):
    """
    [POST] /answer のレスポンスボディの型
    """

    correctIdxes: List[int]
    explanations: List[str]


class PutEn2JaRes(TypedDict):
    """
    [PUT] /en2ja のレスポンスボディの型
    """

    __root__: List[str]
