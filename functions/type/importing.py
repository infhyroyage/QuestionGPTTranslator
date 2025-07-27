"""インポートデータの型定義"""

from typing import List, Optional, TypedDict


class EscapeTranslatedIdxes(TypedDict, total=False):
    """
    インポートデータファイルのescapeTranslatedIdxesフィールドの各要素の型
    """

    subjects: Optional[List[int]]
    """
    翻訳しない問題文のインデックス
    """

    choices: Optional[List[int]]
    """
    翻訳しない選択肢のインデックス
    """


class Discussion(TypedDict, total=False):
    """
    ディスカッションの型
    """

    comment: str
    """
    ユーザーのコメント
    """

    upvotedNum: int
    """
    賛成票数
    """

    selectedAnswer: Optional[str]
    """
    ユーザーが選択した選択肢
    """


class ImportItem(TypedDict):
    """
    インポートデータファイルの各要素の型
    """

    subjects: List[str]
    """
    問題文/画像 URL
    """

    choices: List[str | None]
    """
    選択肢(画像URLのみの場合はNone)
    """

    answerNum: int
    """
    回答の選択肢の個数
    """

    indicateSubjectImgIdxes: Optional[List[int]]
    """
    問題文の文章が画像URLである場合はtrue、そうでない場合はfalse
    """

    indicateChoiceImgs: Optional[List[Optional[str]]]
    """
    選択肢の文に続く画像URL(画像がない場合はNone)
    """

    escapeTranslatedIdxes: Optional[EscapeTranslatedIdxes]
    """
    翻訳しない問題文・選択肢のインデックス
    """

    discussions: Optional[List[Discussion]]
    """
    コミュニティでのディスカッション
    """


class ImportDatabaseData(TypedDict):
    """
    インポートデータをテストごとに集めた型
    """

    __root__: dict[str, List[ImportItem]]
    """
    テストIDをキーとする、各テストの問題データのリストのディクショナリ
    """


class ImportData(TypedDict):
    """
    全テストのインポートデータをコースごとに集めた型
    """

    __root__: dict[str, ImportDatabaseData]
    """
    コース名をキーとする、各テストのインポートデータのディクショナリ
    """
