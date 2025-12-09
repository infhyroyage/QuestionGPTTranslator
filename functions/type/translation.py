"""翻訳エンジンのレスポンスの型定義"""

from typing import List, TypedDict


class AzureTranslatorTranslationsItem(TypedDict):
    """
    Azure Translatorのレスポンスの各要素のtranslationsフィールドの型
    """

    text: str
    """
    Azure Translatorで翻訳した文章
    """

    to: str
    """
    Azure Translatorが検出した言語コード
    """


class AzureTranslatorTranslations(TypedDict):
    """
    Azure Translatorのレスポンスの各要素の型
    """

    translations: List[AzureTranslatorTranslationsItem]
    """
    Azure Translatorの翻訳結果
    """


class AzureTranslatorRes(TypedDict):
    """
    Azure Translatorのレスポンスの型
    """

    __root__: List[AzureTranslatorTranslations]
    """
    Azure Translatorの翻訳結果
    """
