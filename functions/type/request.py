"""関数アプリのHTTPトリガーのリクエストボディの型定義"""

from typing import List, TypedDict


class PutEn2JaReq(TypedDict):
    """
    [PUT] /en2ja のリクエストボディの型
    """

    __root__: List[str]
    """
    英語の各文章
    """


class PostFavoriteReq(TypedDict):
    """
    [POST] /tests/{testId}/favorites/{questionNumber} のリクエストボディの型
    """

    isFavorite: bool
    """
    お気に入りの場合はtrue、そうでない場合はfalse
    """


class PostProgressReq(TypedDict):
    """
    [POST] /tests/{testId}/progresses/{questionNumber} のリクエストボディの型
    """

    isCorrect: bool
    """
    正解の場合はtrue、不正解の場合はfalse
    """

    selectedIdxes: List[int]
    """
    選択した選択肢のインデックス
    """

    correctIdxes: List[int]
    """
    正解の選択肢のインデックス
    """
