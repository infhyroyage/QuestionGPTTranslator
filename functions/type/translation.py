"""Translation Type Definitions"""

from typing import List, TypedDict


class DeepLTranslation(TypedDict):
    """
    Type of elements in the translations array of DeepL response
    """

    detected_source_language: str
    text: str


class DeepLRes(TypedDict):
    """
    Type of DeepL Response
    """

    translations: List[DeepLTranslation]


class AzureTranslatorTranslationsItem(TypedDict):
    """
    Type of elements in the translations array
    """

    text: str
    to: str


class AzureTranslatorTranslations(TypedDict):
    """
    Type of elements in the Azure Translator response array
    """

    translations: List[AzureTranslatorTranslationsItem]


class AzureTranslatorRes(TypedDict):
    """
    Type of Azure Translator Response
    """

    __root__: List[AzureTranslatorTranslations]
