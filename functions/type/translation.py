"""翻訳エンジンのレスポンスの型定義"""

from typing import List, TypedDict


class DeepLTranslation(TypedDict):
    """
    DeepLのレスポンスのtranslationsフィールドの型
    """

    detected_source_language: str
    text: str


class DeepLRes(TypedDict):
    """
    DeepLのレスポンスの型
    """

    translations: List[DeepLTranslation]


class AzureTranslatorTranslationsItem(TypedDict):
    """
    Azure Translatorのレスポンスの各要素のtranslationsフィールドの型
    """

    text: str
    to: str


class AzureTranslatorTranslations(TypedDict):
    """
    Azure Translatorのレスポンスの各要素の型
    """

    translations: List[AzureTranslatorTranslationsItem]


class AzureTranslatorRes(TypedDict):
    """
    Azure Translatorのレスポンスの型
    """

    __root__: List[AzureTranslatorTranslations]
