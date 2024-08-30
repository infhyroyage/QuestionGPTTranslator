"""インポートデータの型定義"""

from typing import List, Optional, TypedDict


class EscapeTranslatedIdxes(TypedDict, total=False):
    """
    インポートデータファイルのescapeTranslatedIdxesフィールドの各要素の型
    """

    subjects: Optional[List[int]]
    choices: Optional[List[int]]


class ImportItem(TypedDict):
    """
    インポートデータファイルの各要素の型
    """

    subjects: List[str]
    choices: List[str]
    communityVotes: List[str]
    indicateSubjectImgIdxes: Optional[List[int]]
    indicateChoiceImgs: Optional[List[Optional[str]]]
    escapeTranslatedIdxes: Optional[EscapeTranslatedIdxes]


class ImportDatabaseData(TypedDict):
    """
    インポートデータをテストごとに集めた型
    """

    __root__: dict[str, List[ImportItem]]


class ImportData(TypedDict):
    """
    全テストのインポートデータをコースごとに集めた型
    """

    __root__: dict[str, ImportDatabaseData]
