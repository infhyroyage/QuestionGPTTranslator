"""[PUT] /en2ja のモジュール"""

import json
import logging
import os
from typing import Optional

import azure.functions as func
import requests
from type.request import PutEn2JaReq
from type.response import PutEn2JaRes
from type.translation import AzureTranslatorRes, DeepLRes


def translate_by_azure_translator(texts: list[str]) -> Optional[list[str]]:
    """
    指定した英語の文字列群をAzure Translatorでそれぞれ日本語に翻訳する
    Azure Translatorの無料枠を使い切った場合はNoneを返す

    Args:
        texts (list[str]): 英語の文字列群

    Returns:
        Optional[list[str]]: 日本語に翻訳した文字列群(Azure Translatorの無料枠を使い切った場合はNone)
    """

    if not texts:
        return []

    translator_key = os.getenv("TRANSLATOR_KEY")
    if not translator_key:
        raise ValueError("Unset TRANSLATOR_KEY")

    headers = {
        "Ocp-Apim-Subscription-Key": translator_key,
        "Ocp-Apim-Subscription-Region": "japaneast",
        "Content-Type": "application/json",
    }
    params = {
        "api-version": "3.0",
        "from": "en",
        "to": "ja",
    }
    body = [{"Text": text} for text in texts]

    try:
        response = requests.post(
            "https://api.cognitive.microsofttranslator.com/translate",
            headers=headers,
            params=params,
            json=body,
            timeout=10,
        )
        response.raise_for_status()
        data: AzureTranslatorRes = response.json()
        return [item["translations"][0]["text"] for item in data]
    except requests.exceptions.RequestException as e:
        # Azure Translatorの無料枠を使い切った場合は403エラーとなる
        if response.status_code == 403:
            return None
        raise e


def translate_by_deep_l(texts: list[str]) -> Optional[list[str]]:
    """
    指定した英語の文字列群をDeepLでそれぞれ日本語に翻訳する
    DeepLの無料枠を使い切った場合はNoneを返す

    Args:
        texts (list[str]): 英語の文字列群

    Returns:
        Optional[list[str]]: 日本語に翻訳した文字列群(DeepLの無料枠を使い切った場合はNone)
    """

    if not texts:
        return []

    auth_key = os.getenv("DEEPL_AUTH_KEY")
    if not auth_key:
        raise ValueError("Unset DEEPL_AUTH_KEY")

    params = {
        "auth_key": auth_key,
        "text": texts,
        "source_lang": "EN",
        "target_lang": "JA",
        "split_sentences": "0",
    }

    try:
        response = requests.get(
            "https://api-free.deepl.com/v2/translate", params=params, timeout=10
        )
        response.raise_for_status()
        data: DeepLRes = response.json()
        return [translation["text"] for translation in data["translations"]]
    except requests.exceptions.RequestException as e:
        # DeepLの無料枠を使い切った場合は456エラーとなる
        if response.status_code == 456:
            return None
        raise e


bp_put_en2ja = func.Blueprint()


@bp_put_en2ja.route(
    route="en2ja",
    methods=["PUT"],
    auth_level=func.AuthLevel.FUNCTION,
)
def put_en2ja(req: func.HttpRequest) -> func.HttpResponse:
    """
    英語の各メッセージを日本語に翻訳します
    """

    try:
        # バリデーションチェック
        texts_encoded: bytes = req.get_body()
        if not texts_encoded:
            return func.HttpResponse(body="Request Body is Empty", status_code=400)
        texts: PutEn2JaReq = json.loads(texts_encoded.decode("utf-8"))
        if not isinstance(texts, list):
            return func.HttpResponse(body=f"Invalid texts: {texts}", status_code=400)
        if len(texts) == 0:
            return func.HttpResponse(body="Request Body is Empty", status_code=400)

        logging.info({"texts": texts})

        # Azure Translatorで翻訳
        # Azure Translatorの無料枠を使い切った場合はWarningログを出力し、代わりにDeepLで翻訳
        json_body = translate_by_azure_translator(texts)
        if json_body is None:
            logging.warning("Azure Translator Free Tier is used up.")
            json_body = translate_by_deep_l(texts)

        logging.info({"body": json_body})
        if json_body is None:
            raise ValueError("Cannot translate texts.")

        body: PutEn2JaRes = json_body
        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
