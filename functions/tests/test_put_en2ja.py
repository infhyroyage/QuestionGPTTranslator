"""[PUT] /en2ja のテスト"""

import json
import os
import unittest
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from requests.exceptions import HTTPError
from src.put_en2ja import (
    put_en2ja,
    translate_by_azure_translator,
    translate_by_deep_l,
    validate_request,
)


class TestValidateRequest(unittest.TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功する場合のテスト"""

        req = func.HttpRequest(
            method="PUT",
            url="/api/en2ja",
            body=json.dumps(["Hello"]).encode("utf-8"),
        )

        result = validate_request(req)

        self.assertIsNone(result)

    def test_validate_request_request_body_empty(self):
        """リクエストボディが空である場合のテスト"""

        req = func.HttpRequest(
            method="PUT",
            url="/api/en2ja",
            body=None,
        )

        result = validate_request(req)

        self.assertEqual(result, "Request Body is Empty")

    def test_validate_request_request_body_not_list(self):
        """リクエストボディがlistでない場合のテスト"""

        req = func.HttpRequest(
            method="PUT",
            url="/api/en2ja",
            body=json.dumps("Hello").encode("utf-8"),
        )

        result = validate_request(req)

        self.assertEqual(result, "Invalid texts: Hello")

    def test_validate_request_request_body_empty_list(self):
        """リクエストボディが空のlistである場合のテスト"""

        req = func.HttpRequest(
            method="PUT",
            url="/api/en2ja",
            body=json.dumps([]).encode("utf-8"),
        )

        result = validate_request(req)

        self.assertEqual(result, "Request Body is Empty")


class TestTranslateByAzureTranslator(unittest.TestCase):
    """translate_by_azure_translator関数のテストケース"""

    @patch("src.put_en2ja.requests.post")
    @patch("src.put_en2ja.logging")
    @patch.dict(os.environ, {"TRANSLATOR_KEY": "fake-key"})
    def test_translate_by_azure_translator_success(self, mock_logging, mock_post):
        """Azure Translatorでの翻訳が成功する場合のテスト"""

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"translations": [{"text": "こんにちは", "to": "ja"}]}
        ]
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = translate_by_azure_translator(["Hello"])
        mock_post.assert_called_once_with(
            "https://api.cognitive.microsofttranslator.com/translate",
            headers={
                "Ocp-Apim-Subscription-Key": "fake-key",
                "Ocp-Apim-Subscription-Region": "japaneast",
                "Content-Type": "application/json",
            },
            params={
                "api-version": "3.0",
                "from": "en",
                "to": "ja",
            },
            json=[{"Text": "Hello"}],
            timeout=10,
        )
        self.assertEqual(result, ["こんにちは"])
        mock_logging.error.assert_not_called()

    @patch("src.put_en2ja.logging")
    def test_translate_by_azure_translator_empty_texts(self, mock_logging):
        """Azure Translatorでの翻訳で空の英語の文字列群を指定した場合のテスト"""

        result = translate_by_azure_translator([])
        self.assertEqual(result, [])
        mock_logging.error.assert_not_called()

    @patch("src.put_en2ja.logging")
    def test_translate_by_azure_translator_unset_key(self, mock_logging):
        """Azure Translatorでの翻訳で環境変数TRANSLATOR_KEYが未設定の場合のテスト"""

        with self.assertRaises(ValueError) as context:
            translate_by_azure_translator(["Hello"])
        self.assertEqual(str(context.exception), "Unset TRANSLATOR_KEY")
        mock_logging.error.assert_not_called()

    @patch("src.put_en2ja.requests.post")
    @patch("src.put_en2ja.logging")
    @patch.dict(os.environ, {"TRANSLATOR_KEY": "fake-key"})
    def test_translate_by_azure_translator_free_tier_used_up(
        self, mock_logging, mock_post
    ):
        """Azure Translatorの無料枠を使い切った場合のテスト"""

        mock_response = MagicMock()
        mock_http_error = HTTPError()
        mock_http_error.response = MagicMock()
        mock_http_error.response.status_code = 403
        mock_response.raise_for_status.side_effect = mock_http_error
        mock_post.return_value = mock_response

        result = translate_by_azure_translator(["Hello"])
        mock_post.assert_called_once_with(
            "https://api.cognitive.microsofttranslator.com/translate",
            headers={
                "Ocp-Apim-Subscription-Key": "fake-key",
                "Ocp-Apim-Subscription-Region": "japaneast",
                "Content-Type": "application/json",
            },
            params={
                "api-version": "3.0",
                "from": "en",
                "to": "ja",
            },
            json=[{"Text": "Hello"}],
            timeout=10,
        )
        self.assertIsNone(result)
        mock_logging.error.assert_called_once()

    @patch("src.put_en2ja.requests.post")
    @patch("src.put_en2ja.logging")
    @patch.dict(os.environ, {"TRANSLATOR_KEY": "fake-key"})
    def test_translate_by_azure_translator_exception(self, mock_logging, mock_post):
        """Azure Translatorでの翻訳で例外が発生する場合のテスト"""

        mock_response = MagicMock()
        mock_http_error = HTTPError()
        mock_http_error.response = MagicMock()
        mock_http_error.response.status_code = 500
        mock_response.raise_for_status.side_effect = mock_http_error
        mock_post.return_value = mock_response

        with self.assertRaises(HTTPError):
            translate_by_azure_translator(["Hello"])
        mock_logging.error.assert_called_once()


class TestTranslateByDeepL(unittest.TestCase):
    """translate_by_deep_l関数のテストケース"""

    @patch("src.put_en2ja.requests.get")
    @patch("src.put_en2ja.logging")
    @patch.dict(os.environ, {"DEEPL_AUTH_KEY": "fake-key"})
    def test_translate_by_deep_l_success(self, mock_logging, mock_get):
        """DeepLでの翻訳が成功する場合のテスト"""

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "translations": [{"text": "こんにちは", "detected_source_language": "EN"}]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = translate_by_deep_l(["Hello"])
        mock_get.assert_called_once_with(
            "https://api-free.deepl.com/v2/translate",
            params={
                "auth_key": "fake-key",
                "text": ["Hello"],
                "source_lang": "EN",
                "target_lang": "JA",
                "split_sentences": "0",
            },
            timeout=10,
        )
        self.assertEqual(result, ["こんにちは"])
        mock_logging.error.assert_not_called()

    @patch("src.put_en2ja.logging")
    def test_translate_by_deep_l_empty_texts(self, mock_logging):
        """DeepLでの翻訳で空の英語の文字列群を指定した場合のテスト"""

        result = translate_by_deep_l([])
        self.assertEqual(result, [])
        mock_logging.error.assert_not_called()

    @patch("src.put_en2ja.logging")
    def test_translate_by_deep_l_unset_key(self, mock_logging):
        """DeepLでの翻訳で環境変数DEEPL_AUTH_KEYが未設定の場合のテスト"""
        with self.assertRaises(ValueError) as context:
            translate_by_deep_l(["Hello"])
        self.assertEqual(str(context.exception), "Unset DEEPL_AUTH_KEY")
        mock_logging.error.assert_not_called()

    @patch("src.put_en2ja.requests.get")
    @patch("src.put_en2ja.logging")
    @patch.dict(os.environ, {"DEEPL_AUTH_KEY": "fake-key"})
    def test_translate_by_deep_l_free_tier_used_up(self, mock_logging, mock_get):
        """DeepLの無料枠を使い切った場合のテスト"""

        mock_response = MagicMock()
        mock_http_error = HTTPError()
        mock_http_error.response = MagicMock()
        mock_http_error.response.status_code = 456
        mock_response.raise_for_status.side_effect = mock_http_error
        mock_get.return_value = mock_response

        result = translate_by_deep_l(["Hello"])
        mock_get.assert_called_once_with(
            "https://api-free.deepl.com/v2/translate",
            params={
                "auth_key": "fake-key",
                "text": ["Hello"],
                "source_lang": "EN",
                "target_lang": "JA",
                "split_sentences": "0",
            },
            timeout=10,
        )
        self.assertIsNone(result)
        mock_logging.error.assert_called_once()

    @patch("src.put_en2ja.requests.get")
    @patch("src.put_en2ja.logging")
    @patch.dict(os.environ, {"DEEPL_AUTH_KEY": "fake-key"})
    def test_translate_by_deep_l_exception(self, mock_logging, mock_get):
        """DeepLでの翻訳で例外が発生する場合のテスト"""

        mock_response = MagicMock()
        mock_http_error = HTTPError()
        mock_http_error.response = MagicMock()
        mock_http_error.response.status_code = 500
        mock_response.raise_for_status.side_effect = mock_http_error
        mock_get.return_value = mock_response

        with self.assertRaises(HTTPError):
            translate_by_deep_l(["Hello"])
        mock_logging.error.assert_called_once()


class TestPutEn2Ja(unittest.TestCase):
    """put_en2ja関数のテストケース"""

    @patch("src.put_en2ja.validate_request")
    @patch("src.put_en2ja.translate_by_azure_translator")
    @patch("src.put_en2ja.logging")
    def test_put_en2ja_success(
        self, mock_logging, mock_translate_by_azure_translator, mock_validate_request
    ):
        """レスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_translate_by_azure_translator.return_value = [
            "Azure Translatorからこんにちは"
        ]
        req = func.HttpRequest(
            method="PUT",
            url="/api/en2ja",
            body=json.dumps(["Hello from Azure Translator"]).encode("utf-8"),
        )

        response = put_en2ja(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_body(),
            json.dumps(["Azure Translatorからこんにちは"]).encode("utf-8"),
        )
        mock_validate_request.assert_called_once_with(req)
        mock_translate_by_azure_translator.assert_called_once_with(
            ["Hello from Azure Translator"]
        )
        mock_logging.info.assert_has_calls(
            [
                call({"texts": ["Hello from Azure Translator"]}),
                call({"body": ["Azure Translatorからこんにちは"]}),
            ]
        )
        mock_logging.warning.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.put_en2ja.validate_request")
    def test_put_en2ja_validation_error(self, mock_validate_request):
        """バリデーションチェックに失敗した場合のテスト"""

        mock_validate_request.return_value = "Validation Error"

        req = MagicMock(spec=func.HttpRequest)
        req.get_body.return_value = json.dumps(
            {
                "courseName": "Math",
                "subjects": ["What is 2 + 2?"],
                "choices": ["3", "4", "5"],
            }
        ).encode("utf-8")

        response = put_en2ja(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_body().decode(), "Validation Error")
        mock_validate_request.assert_called_once_with(req)

    @patch("src.put_en2ja.validate_request")
    @patch("src.put_en2ja.translate_by_deep_l")
    @patch("src.put_en2ja.translate_by_azure_translator")
    @patch("src.put_en2ja.logging")
    def test_put_en2ja_azure_free_tier_used_up(
        self,
        mock_logging,
        mock_translate_by_azure_translator,
        mock_translate_by_deep_l,
        mock_validate_request,
    ):
        """Azure Translator無料枠を使い切った場合のテスト"""

        mock_validate_request.return_value = None
        mock_translate_by_azure_translator.return_value = None
        mock_translate_by_deep_l.return_value = ["DeepLからこんにちは"]
        req = func.HttpRequest(
            method="PUT",
            url="/api/en2ja",
            body=json.dumps(["Hello from DeepL"]).encode("utf-8"),
        )

        response = put_en2ja(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_body(),
            json.dumps(["DeepLからこんにちは"]).encode("utf-8"),
        )
        mock_validate_request.assert_called_once_with(req)
        mock_translate_by_azure_translator.assert_called_once_with(["Hello from DeepL"])
        mock_translate_by_deep_l.assert_called_once_with(["Hello from DeepL"])
        mock_logging.info.assert_has_calls(
            [
                call({"texts": ["Hello from DeepL"]}),
                call({"body": ["DeepLからこんにちは"]}),
            ]
        )
        mock_logging.warning.assert_called_once_with(
            "Azure Translator Free Tier is used up."
        )
        mock_logging.error.assert_not_called()

    @patch("src.put_en2ja.validate_request")
    @patch("src.put_en2ja.translate_by_deep_l")
    @patch("src.put_en2ja.translate_by_azure_translator")
    @patch("src.put_en2ja.logging")
    def test_put_en2ja_both_free_tier_used_up(
        self,
        mock_logging,
        mock_translate_by_azure_translator,
        mock_translate_by_deep_l,
        mock_validate_request,
    ):
        """put_en2ja関数のAzure TranslatorとDeepLの両方の無料枠を使い切った場合のテスト"""

        mock_validate_request.return_value = None
        mock_translate_by_azure_translator.return_value = None
        mock_translate_by_deep_l.return_value = None
        req = func.HttpRequest(
            method="PUT",
            url="/api/en2ja",
            body=json.dumps(["Hello"]).encode("utf-8"),
        )

        response = put_en2ja(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body(), b"Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_translate_by_azure_translator.assert_called_once_with(["Hello"])
        mock_translate_by_deep_l.assert_called_once_with(["Hello"])
        mock_logging.info.assert_has_calls(
            [
                call({"texts": ["Hello"]}),
                call({"body": None}),
            ]
        )
        mock_logging.warning.assert_called_once_with(
            "Azure Translator Free Tier is used up."
        )
        mock_logging.error.assert_called_once()

    @patch("src.put_en2ja.validate_request")
    @patch("src.put_en2ja.translate_by_azure_translator")
    @patch("src.put_en2ja.logging")
    def test_put_en2ja_exception(
        self,
        mock_logging,
        mock_translate_by_azure_translator,
        mock_validate_request,
    ):
        """例外が発生した場合のテスト"""

        mock_validate_request.return_value = None
        mock_translate_by_azure_translator.side_effect = Exception()
        req = func.HttpRequest(
            method="PUT",
            url="/api/en2ja",
            body=json.dumps(["Hello"]).encode("utf-8"),
        )

        response = put_en2ja(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body(), b"Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_called_once_with({"texts": ["Hello"]})
        mock_logging.warning.assert_not_called()
        mock_logging.error.assert_called_once()
