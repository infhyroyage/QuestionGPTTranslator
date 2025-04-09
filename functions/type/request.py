"""関数アプリのHTTPトリガーのリクエストボディの型定義"""

from typing import List, Optional, TypedDict


class PutEn2JaReq(TypedDict):
    """
    [PUT] /en2ja のリクエストボディの型
    """

    __root__: List[str]


class PostProgressReq(TypedDict):
    """
    [POST] /tests/{testId}/progresses/{questionNumber} のリクエストボディの型
    """

    isCorrect: bool
    choiceSentences: List[str]
    choiceImgs: List[Optional[str]]
    choiceTranslations: Optional[List[str]]
    selectedIdxes: List[int]
    correctIdxes: List[int]
