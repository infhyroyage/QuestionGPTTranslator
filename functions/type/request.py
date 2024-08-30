"""関数アプリのHTTPトリガーのリクエストボディの型定義"""

from typing import List, TypedDict


class PostAnswerReq(TypedDict):
    """
    [POST] /answer のリクエストボディの型
    """

    courseName: str
    subjects: List[str]
    choices: List[str]


class PutEn2JaReq(TypedDict):
    """
    [PUT] /en2ja のリクエストボディの型
    """

    __root__: List[str]
