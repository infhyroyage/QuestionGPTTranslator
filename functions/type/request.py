"""関数アプリのHTTPトリガーのリクエストボディの型定義"""

from typing import List, TypedDict


class PutEn2JaReq(TypedDict):
    """
    [PUT] /en2ja のリクエストボディの型
    """

    __root__: List[str]
