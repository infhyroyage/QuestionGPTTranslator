"""Functions Application Request Type Definitions"""

from typing import List, TypedDict


class PostAnswerReq(TypedDict):
    """
    [POST] /answer Request Type
    """

    courseName: str
    questionNumber: int
    testId: str
    subjects: List[str]
    choices: List[str]


class PutEn2JaReq(TypedDict):
    """
    [PUT] /en2ja Request Type
    """

    __root__: List[str]
