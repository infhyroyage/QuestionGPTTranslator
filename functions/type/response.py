"""関数アプリのHTTPトリガーのレスポンスボディの型定義"""

from typing import List, Optional, TypedDict


class PutEn2JaRes(TypedDict):
    """
    [PUT] /en2ja のレスポンスボディの型
    """

    __root__: List[str]
    """
    英語の各文章を和訳した文章
    """


class GetHealthcheckRes(TypedDict):
    """
    [GET] /healthcheck のレスポンスボディの型
    """

    __root__: str
    """
    ヘルスチェックの結果
    """


class Test(TypedDict):
    """
    [GET] /tests のレスポンスボディの各要素の型
    """

    id: str
    """
    テストID
    """

    testName: str
    """
    テスト名
    """

    length: int
    """
    テストの問題数
    """


class GetTestsRes(TypedDict):
    """
    [GET] /tests のレスポンスボディの型
    """

    __root__: dict[str, List[Test]]
    """
    コース名をキーとする、各テストのディクショナリ
    """


class GetAnswerRes(TypedDict):
    """
    [GET] /tests/{testId}/answers/{questionNumber} のレスポンスボディの型
    """

    correctIdxes: Optional[List[int]]
    """
    正解の選択肢のインデックス
    """

    explanations: Optional[List[str]]
    """
    各選択肢の正解/不正解の理由
    """

    isExisted: bool
    """
    正解の選択肢・正解/不正解の理由が存在する場合はtrue、存在しない場合はfalse
    """


class PostAnswerRes(TypedDict, total=False):
    """
    [POST] /tests/{testId}/answers/{questionNumber} のレスポンスボディの型
    """

    correctIdxes: List[int]
    """
    正解の選択肢のインデックス
    """

    explanations: List[str]
    """
    各選択肢の正解/不正解の理由
    """


class GetCommunityRes(TypedDict):
    """
    [GET] /tests/{testId}/communities/{questionNumber} のレスポンスボディの型
    """

    discussionsSummary: Optional[str]
    """
    コミュニティでのディスカッションの要約
    """

    votes: Optional[List[str]]
    """
    コミュニティでの回答の割合
    """

    isExisted: bool
    """
    コミュニティでのディスカッションの要約が存在する場合はtrue、存在しない場合はfalse
    """


class PostCommunityRes(TypedDict):
    """
    [POST] /tests/{testId}/communities/{questionNumber} のレスポンスボディの型
    """

    discussionsSummary: Optional[str]
    """
    コミュニティでのディスカッションの要約
    """

    votes: Optional[List[str]]
    """
    コミュニティでの回答の割合
    """

    isExisted: bool
    """
    コミュニティでのディスカッションの要約が存在する場合はtrue、存在しない場合はfalse
    """


class GetFavoriteRes(TypedDict):
    """
    [GET] /tests/{testId}/favorites/{questionNumber} のレスポンスボディの型
    """

    isFavorite: bool
    """
    お気に入りの場合はtrue、そうでない場合はfalse
    """


class Favorite(TypedDict):
    """
    [GET] /tests/{testId}/favorites のレスポンスボディの各要素の型
    """

    questionNumber: int
    """
    問題番号
    """

    isFavorite: bool
    """
    お気に入りの場合はtrue、そうでない場合はfalse
    """


class GetFavoritesRes(TypedDict):
    """
    [GET] /tests/{testId}/favorites のレスポンスボディの型
    """

    __root__: List[Favorite]
    """
    お気に入りの場合はtrue、そうでない場合はfalse(問題番号の昇順)
    """


class Progress(TypedDict):
    """
    [GET] /tests/{testId}/progresses のレスポンスボディの各要素の型
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


class GetProgressesRes(TypedDict):
    """
    [GET] /tests/{testId}/progresses のレスポンスボディの型
    """

    order: List[int]
    """
    テストを解く問題番号の順番
    """

    progresses: List[Progress]
    """
    問題番号の順番に対応する進捗項目
    """


class PostProgressRes(TypedDict):
    """
    [POST] /tests/{testId}/progresses/{questionNumber} のレスポンスボディの型
    """

    __root__: List[Progress]
    """
    保存後の問題番号の順番に対応する進捗項目
    """


class Subject(TypedDict):
    """
    [GET] /tests/{testId}/questions/{questionNumber} のレスポンスボディのsubjectsフィールドの各要素の型
    """

    sentence: str
    """
    問題文
    """

    isIndicatedImg: bool
    """
    問題文の文章が画像URLである場合はtrue、そうでない場合はfalse
    """

    isEscapedTranslation: bool
    """
    翻訳不要の場合はtrue、翻訳する場合はfalse
    """


class Choice(TypedDict):
    """
    [GET] /tests/{testId}/questions/{questionNumber} のレスポンスボディのchoicesフィールドの各要素の型
    """

    sentence: Optional[str]
    """
    選択肢の文(画像URLのみの場合はNone)
    """

    img: Optional[str]
    """
    選択肢の文に続く画像URL(画像がない場合はNone)
    """

    isEscapedTranslation: bool
    """
    翻訳不要の場合はtrue、翻訳する場合はfalse
    """


class GetQuestionRes(TypedDict):
    """
    [GET] /tests/{testId}/questions/{questionNumber} のレスポンスボディの型
    """

    subjects: List[Subject]
    """
    各問題文
    """

    choices: List[Choice]
    """
    各選択肢の文
    """

    isMultiplied: bool
    """
    回答が複数個の場合はtrue、回答が1個の場合はfalse
    """
