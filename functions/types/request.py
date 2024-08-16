"""
Functions Application Request Type Definitions
"""

from typing import List, TypedDict


class PostAnsterReq(TypedDict):
    """
    [POST] /answer Request Type
    """

    subjects: List[str]
    choices: List[str]


class PutEn2JaReq(TypedDict):
    """
    [PUT] /en2ja Request Type
    """

    __root__: List[str]
