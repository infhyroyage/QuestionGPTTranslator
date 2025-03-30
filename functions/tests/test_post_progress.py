"""post_progress関数のテスト"""

import json
import unittest
from unittest.mock import MagicMock, patch

import azure.functions as func
from src.post_progress import post_progress, validate_request


class TestValidateRequest(unittest.TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertIsNone(error_message)

    def test_validate_request_empty_test_id(self):
        """testIdが空である場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests//progresses/1",
            route_params={"testId": "", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "testId is Empty")

    def test_validate_request_empty_question_number(self):
        """questionNumberが空である場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/",
            route_params={"testId": "test-id", "questionNumber": ""},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "questionNumber is Empty")

    def test_validate_request_invalid_question_number(self):
        """questionNumberが数字ではない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/abc",
            route_params={"testId": "test-id", "questionNumber": "abc"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid questionNumber: abc")

    def test_validate_request_empty_user_id(self):
        """X-User-Idヘッダーが空である場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "X-User-Id header is Empty")

    def test_validate_request_empty_body(self):
        """リクエストボディが空である場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=None,
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Request Body is Empty")

    def test_validate_request_missing_is_correct(self):
        """リクエストボディにisCorrectが存在しない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "isCorrect is required")

    def test_validate_request_invalid_is_correct(self):
        """isCorrectがboolでない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": "true",
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid isCorrect: true")

    def test_validate_request_missing_choice_sentences(self):
        """リクエストボディにchoiceSentencesが存在しない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "choiceSentences is required")

    def test_validate_request_invalid_choice_sentences(self):
        """choiceSentencesがlistでない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": "選択肢1",
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid choiceSentences: 選択肢1")

    def test_validate_request_invalid_choice_sentence_item(self):
        """choiceSentencesの要素が文字列でない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", 2],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid choiceSentences[1]: 2")

    def test_validate_request_missing_choice_imgs(self):
        """リクエストボディにchoiceImgsが存在しない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "choiceImgs is required")

    def test_validate_request_invalid_choice_imgs(self):
        """choiceImgsがlistでない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": "https://example.com/img.png",
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(
            error_message, "Invalid choiceImgs: https://example.com/img.png"
        )

    def test_validate_request_invalid_choice_img_item(self):
        """choiceImgsの要素が文字列でない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, 123],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid choiceImgs[1]: 123")

    def test_validate_request_invalid_choice_translations(self):
        """choiceTranslationsがlistでない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": "選択肢1の翻訳",
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid choiceTranslations: 選択肢1の翻訳")

    def test_validate_request_invalid_choice_translation_item(self):
        """choiceTranslationsの要素が文字列でない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": [
                        "選択肢1の翻訳",
                        123,
                    ],
                    "selectedIdxes": [0],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid choiceTranslations[1]: 123")

    def test_validate_request_missing_selected_idxes(self):
        """リクエストボディにselectedIdxesが存在しない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "selectedIdxes is required")

    def test_validate_request_invalid_selected_idxes(self):
        """selectedIdxesがlistでない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": 0,
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid selectedIdxes: 0")

    def test_validate_request_invalid_selected_idx_item(self):
        """selectedIdxesの要素が数値でない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0, "1"],
                    "correctIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid selectedIdxes[1]: 1")

    def test_validate_request_missing_correct_idxes(self):
        """リクエストボディにcorrectIdxesが存在しない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "correctIdxes is required")

    def test_validate_request_invalid_correct_idxes(self):
        """correctIdxesがlistでない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": 0,
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid correctIdxes: 0")

    def test_validate_request_invalid_correct_idx_item(self):
        """correctIdxesの要素が数値でない場合のテスト"""

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0],
                    "correctIdxes": [0, "1"],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )
        error_message = validate_request(req)
        self.assertEqual(error_message, "Invalid correctIdxes[1]: 1")


class TestPostProgress(unittest.TestCase):
    """post_progress関数のテストケース"""

    @patch("src.post_progress.validate_request")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_success(
        self, mock_logging, mock_get_read_write_container, mock_validate_request
    ):
        """正常系のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0, 1],
            "correctIdxes": [2, 3],
        }
        req = func.HttpRequest(
            method="POST",
            body=json.dumps(req_body).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        resp = post_progress(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_body().decode("utf-8"), "OK")
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users", container_name="Progress"
        )
        mock_container.upsert_item.assert_called_once_with(
            body={
                "userId": "user-id",
                "testId": "test-id",
                "questionNumber": 1,
                "isCorrect": True,
                "choiceSentences": ["選択肢1", "選択肢2"],
                "choiceImgs": [None, "https://example.com/img.png"],
                "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                "selectedIdxes": [0, 1],
                "correctIdxes": [2, 3],
            }
        )
        mock_logging.info.assert_called_once_with(
            {
                "question_number": 1,
                "test_id": "test-id",
                "user_id": "user-id",
            }
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_request")
    @patch("src.post_progress.logging")
    def test_post_progress_validation_error(self, mock_logging, mock_validate_request):
        """バリデーションチェックに失敗した場合のテスト"""

        mock_validate_request.return_value = "Validation Error"

        req = func.HttpRequest(
            method="POST",
            body=b"{}",
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        resp = post_progress(req)

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_body().decode("utf-8"), "Validation Error")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_request")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_exception(
        self, mock_logging, mock_get_read_write_container, mock_validate_request
    ):
        """例外が発生した場合のテスト"""

        mock_validate_request.return_value = None
        mock_get_read_write_container.side_effect = Exception(
            "Error in src.post_progress.get_read_write_container"
        )

        req = func.HttpRequest(
            method="POST",
            body=json.dumps(
                {
                    "isCorrect": True,
                    "choiceSentences": ["選択肢1", "選択肢2"],
                    "choiceImgs": [None, "https://example.com/img.png"],
                    "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                    "selectedIdxes": [0, 1],
                    "correctIdxes": [2, 3],
                }
            ).encode("utf-8"),
            url="/api/tests/test-id/progresses/1",
            route_params={"testId": "test-id", "questionNumber": "1"},
            headers={"X-User-Id": "user-id"},
        )

        resp = post_progress(req)

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.get_body().decode("utf-8"), "Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.info.assert_called_once_with(
            {
                "question_number": 1,
                "test_id": "test-id",
                "user_id": "user-id",
            }
        )
        mock_logging.error.assert_called_once()
