"""Import Data Type Definitions"""

from typing import List, Optional, TypedDict


class EscapeTranslatedIdxes(TypedDict, total=False):
    """
    Type of escapeTranslatedIdxes in the array elements of the import data file
    """

    subjects: Optional[List[int]]
    choices: Optional[List[int]]


class ImportItem(TypedDict):
    """
    Type of array elements in the import data file
    """

    subjects: List[str]
    choices: List[str]
    communityVotes: List[str]
    indicateSubjectImgIdxes: Optional[List[int]]
    indicateChoiceImgs: Optional[List[Optional[str]]]
    escapeTranslatedIdxes: Optional[EscapeTranslatedIdxes]


class ImportDatabaseData(TypedDict):
    """
    Type that aggregates all import data files for each test
    """

    __root__: dict[str, List[ImportItem]]


class ImportData(TypedDict):
    """
    Type that aggregates all import data files for tests by course
    """

    __root__: dict[str, ImportDatabaseData]
