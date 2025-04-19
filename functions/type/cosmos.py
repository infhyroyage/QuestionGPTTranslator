"""Cosmos DBの項目の型定義"""

from typing import List, Optional, TypedDict


class Answer(TypedDict):
    """
    Answerコンテナーの項目の型
    """

    id: str
    """
    ドキュメントID (= "{テストID}_{問題番号}")
    """

    questionNumber: int
    """
    問題番号
    """

    correctIdxes: List[int]
    """
    正解の選択肢のインデックス
    """

    explanations: List[str]
    """
    各選択肢の正解/不正解の理由
    """

    communityVotes: List[str]
    """
    コミュニティ回答割合
    """

    testId: str
    """
    テストID
    """


class Favorite(TypedDict):
    """
    Favoriteコンテナーの項目の型
    """

    id: str
    """
    ドキュメントID (= "{ユーザーID}_{テストID}_{問題番号}")
    """

    userId: str
    """
    ユーザーID
    """

    testId: str
    """
    テストID
    """

    questionNumber: int
    """
    問題番号
    """

    isFavorite: bool
    """
    お気に入りの場合はtrue、そうでない場合はfalse
    """


class ProgressElement(TypedDict):
    """
    Progressコンテナーのprogressesフィールドの要素の型
    """

    isCorrect: bool
    """
    正解の場合はtrue、不正解の場合はfalse
    """

    choiceSentences: List[str]
    """
    選択肢の文
    """

    choiceImgs: List[Optional[str]]
    """
    選択肢の文に続く画像URL(画像がない場合はNone)
    """

    selectedIdxes: List[int]
    """
    選択した選択肢のインデックス
    """

    correctIdxes: List[int]
    """
    正解の選択肢のインデックス
    """


class Progress(TypedDict):
    """
    Progressコンテナーの項目の型
    """

    id: str
    """
    ドキュメントID (= "{テストID}_{ユーザーID}")
    """

    userId: str
    """
    ユーザーID
    """

    testId: str
    """
    テストID
    """

    progresses: List[ProgressElement]
    """
    全進捗項目
    """


class EscapeTranslatedIdxes(TypedDict, total=False):
    """
    QuestionコンテナーのescapeTranslatedIdxesフィールドの型
    """

    subjects: Optional[List[int]]
    """
    翻訳しない問題文のインデックス
    """

    choices: Optional[List[int]]
    """
    翻訳しない選択肢のインデックス
    """


class Question(TypedDict):
    """
    Questionコンテナーの項目の型
    """

    id: str
    """
    ドキュメントID (= "{テストID}_{問題番号}")
    """

    number: int
    """
    問題番号
    """

    subjects: List[str]
    """
    問題文
    """

    choices: List[str]
    """
    選択肢
    """

    isMultiplied: bool
    """
    回答が複数個の場合はtrue、回答が1個の場合はfalse
    """

    communityVotes: List[str]
    """
    コミュニティ回答割合
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

    testId: str
    """
    テストID
    """


class Test(TypedDict):
    """
    Testコンテナーの項目の型
    """

    id: str
    """
    テストID
    """

    courseName: str
    """
    コース名
    """

    testName: str
    """
    テスト名
    """

    length: int
    """
    テストの問題数
    """
