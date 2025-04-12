"""post_progress関数のテスト"""

import json
import unittest
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from src.post_progress import (
    post_progress,
    validate_body,
    validate_headers,
    validate_route_params,
)


class TestValidateBody(unittest.TestCase):
    """validate_body関数のテストケース"""

    def test_validate_body_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, [])

    def test_validate_body_empty(self):
        """リクエストボディが空の場合のテスト"""

        req_body_encoded = None
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Request Body is Empty"])

    def test_validate_body_missing_is_correct(self):
        """リクエストボディにisCorrectが存在しない場合のテスト"""

        req_body = {
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["isCorrect is required"])

    def test_validate_body_invalid_is_correct(self):
        """isCorrectがboolでない場合のテスト"""

        req_body = {
            "isCorrect": "true",
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid isCorrect: true"])

    def test_validate_body_missing_choice_sentences(self):
        """リクエストボディにchoiceSentencesが存在しない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["choiceSentences is required"])

    def test_validate_body_invalid_choice_sentences(self):
        """choiceSentencesがlistでない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": "選択肢1",
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid choiceSentences: 選択肢1"])

    def test_validate_body_invalid_choice_sentence_item(self):
        """choiceSentencesの要素が文字列でない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", 2],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid choiceSentences[1]: 2"])

    def test_validate_body_missing_choice_imgs(self):
        """リクエストボディにchoiceImgsが存在しない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["choiceImgs is required"])

    def test_validate_body_invalid_choice_imgs(self):
        """choiceImgsがlistでない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": "https://example.com/img.png",
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid choiceImgs: https://example.com/img.png"])

    def test_validate_body_invalid_choice_img_item(self):
        """choiceImgsの要素が文字列でない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, 2],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid choiceImgs[1]: 2"])

    def test_validate_body_invalid_choice_translations(self):
        """choiceTranslationsがlistでない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": "選択肢1の翻訳",
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid choiceTranslations: 選択肢1の翻訳"])

    def test_validate_body_invalid_choice_translation_item(self):
        """choiceTranslationsの要素が文字列でない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", 2],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid choiceTranslations[1]: 2"])

    def test_validate_body_missing_selected_idxes(self):
        """リクエストボディにselectedIdxesが存在しない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["selectedIdxes is required"])

    def test_validate_body_invalid_selected_idxes(self):
        """selectedIdxesがlistでない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": 0,
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid selectedIdxes: 0"])

    def test_validate_body_invalid_selected_idx_item(self):
        """selectedIdxesの要素が数値でない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0, "1"],
            "correctIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid selectedIdxes[1]: 1"])

    def test_validate_body_missing_correct_idxes(self):
        """リクエストボディにcorrectIdxesが存在しない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["correctIdxes is required"])

    def test_validate_body_invalid_correct_idxes(self):
        """correctIdxesがlistでない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": 0,
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid correctIdxes: 0"])

    def test_validate_body_invalid_correct_idx_item(self):
        """correctIdxesの要素が数値でない場合のテスト"""

        req_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0, "1"],
        }
        req_body_encoded = json.dumps(req_body).encode("utf-8")
        errors = validate_body(req_body_encoded)
        self.assertEqual(errors, ["Invalid correctIdxes[1]: 1"])


class TestValidateRouteParams(unittest.TestCase):
    """validate_route_params関数のテストケース"""

    def test_validate_route_params_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        route_params = {"testId": "test-id", "questionNumber": "1"}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, [])

    def test_validate_route_params_empty_test_id(self):
        """testIdが空である場合のテスト"""

        route_params = {"testId": "", "questionNumber": "1"}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, ["testId is Empty"])

    def test_validate_route_params_empty_question_number(self):
        """questionNumberが空である場合のテスト"""

        route_params = {"testId": "test-id", "questionNumber": ""}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, ["questionNumber is Empty"])

    def test_validate_route_params_invalid_question_number(self):
        """questionNumberが数字ではない場合のテスト"""

        route_params = {"testId": "test-id", "questionNumber": "abc"}
        errors = validate_route_params(route_params)
        self.assertEqual(errors, ["Invalid questionNumber: abc"])


class TestValidateHeaders(unittest.TestCase):
    """validate_headers関数のテストケース"""

    def test_validate_headers_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        headers = {"X-User-Id": "user-id"}
        errors = validate_headers(headers)
        self.assertEqual(errors, [])

    def test_validate_headers_empty_user_id(self):
        """X-User-Idヘッダーが空である場合のテスト"""

        headers = {}
        errors = validate_headers(headers)
        self.assertEqual(errors, ["X-User-Id header is Empty"])


class TestPostProgress(unittest.TestCase):
    """post_progress関数のテストケース"""

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_success(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """レスポンスが正常であることのテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.return_value = [{"maxQuestionNumber": 2}]

        request_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/3",
            route_params={"testId": "test-id", "questionNumber": "3"},
            headers={"X-User-Id": "user-id"},
        )
        res = post_progress(req)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_body().decode("utf-8"), "OK")
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users",
            container_name="Progress",
        )
        mock_container.query_items.assert_called_once_with(
            query=(
                "SELECT MAX(c.questionNumber) as maxQuestionNumber "
                "FROM c WHERE c.userId = @userId AND c.testId = @testId"
            ),
            parameters=[
                {"name": "@userId", "value": "user-id"},
                {"name": "@testId", "value": "test-id"},
            ],
            partition_key="test-id",
        )
        mock_container.upsert_item.assert_called_once_with(
            json.loads(
                json.dumps(
                    {
                        "id": "user-id_test-id_3",
                        "userId": "user-id",
                        "testId": "test-id",
                        "questionNumber": 3,
                        "isCorrect": True,
                        "choiceSentences": ["選択肢1", "選択肢2"],
                        "choiceImgs": [None, "https://example.com/img.png"],
                        "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
                        "selectedIdxes": [0],
                        "correctIdxes": [0],
                    },
                    ensure_ascii=False,
                )
            )
        )
        mock_logging.info.assert_has_calls(
            [
                call(
                    {
                        "question_number": 3,
                        "test_id": "test-id",
                        "user_id": "user-id",
                    }
                ),
                call({"items": [{"maxQuestionNumber": 2}]}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.logging")
    def test_post_progress_validation_error(
        self,
        mock_logging,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """バリデーションエラーが発生した場合のテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = ["Validation Error"]

        request_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/3",
            route_params={"testId": "test-id", "questionNumber": "3"},
            headers={"X-User-Id": "user-id"},
        )
        res = post_progress(req)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_body().decode("utf-8"), "Validation Error")
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_invalid_question_number_without_saved_progress(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """何も回答履歴を保存していない場合に、誤った問題番号を指定した場合のテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.return_value = [{"maxQuestionNumber": None}]

        request_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/3",
            route_params={"testId": "test-id", "questionNumber": "3"},
            headers={"X-User-Id": "user-id"},
        )
        res = post_progress(req)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_body().decode("utf-8"), "questionNumber must be 1")
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users",
            container_name="Progress",
        )
        mock_container.query_items.assert_called_once_with(
            query=(
                "SELECT MAX(c.questionNumber) as maxQuestionNumber "
                "FROM c WHERE c.userId = @userId AND c.testId = @testId"
            ),
            parameters=[
                {"name": "@userId", "value": "user-id"},
                {"name": "@testId", "value": "test-id"},
            ],
            partition_key="test-id",
        )
        mock_container.upsert_item.assert_not_called()
        mock_logging.info.assert_has_calls(
            [
                call(
                    {
                        "question_number": 3,
                        "test_id": "test-id",
                        "user_id": "user-id",
                    }
                ),
                call({"items": [{"maxQuestionNumber": None}]}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_invalid_question_number_with_saved_progress(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """途中まで回答履歴を保存した場合に、誤った問題番号を指定した場合のテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = []
        mock_container = MagicMock()
        mock_get_read_write_container.return_value = mock_container
        mock_container.query_items.return_value = [{"maxQuestionNumber": 1}]

        request_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/3",
            route_params={"testId": "test-id", "questionNumber": "3"},
            headers={"X-User-Id": "user-id"},
        )
        res = post_progress(req)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.get_body().decode("utf-8"), "questionNumber must be 1 or 2"
        )
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_get_read_write_container.assert_called_once_with(
            database_name="Users",
            container_name="Progress",
        )
        mock_container.query_items.assert_called_once_with(
            query=(
                "SELECT MAX(c.questionNumber) as maxQuestionNumber "
                "FROM c WHERE c.userId = @userId AND c.testId = @testId"
            ),
            parameters=[
                {"name": "@userId", "value": "user-id"},
                {"name": "@testId", "value": "test-id"},
            ],
            partition_key="test-id",
        )
        mock_container.upsert_item.assert_not_called()
        mock_logging.info.assert_has_calls(
            [
                call(
                    {
                        "question_number": 3,
                        "test_id": "test-id",
                        "user_id": "user-id",
                    }
                ),
                call({"items": [{"maxQuestionNumber": 1}]}),
            ]
        )
        mock_logging.error.assert_not_called()

    @patch("src.post_progress.validate_route_params")
    @patch("src.post_progress.validate_headers")
    @patch("src.post_progress.validate_body")
    @patch("src.post_progress.get_read_write_container")
    @patch("src.post_progress.logging")
    def test_post_progress_exception(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        mock_logging,
        mock_get_read_write_container,
        mock_validate_body,
        mock_validate_headers,
        mock_validate_route_params,
    ):
        """例外が発生した場合のテスト"""

        mock_validate_route_params.return_value = []
        mock_validate_headers.return_value = []
        mock_validate_body.return_value = []
        mock_get_read_write_container.side_effect = Exception("Test Exception")

        request_body = {
            "isCorrect": True,
            "choiceSentences": ["選択肢1", "選択肢2"],
            "choiceImgs": [None, "https://example.com/img.png"],
            "choiceTranslations": ["選択肢1の翻訳", "選択肢2の翻訳"],
            "selectedIdxes": [0],
            "correctIdxes": [0],
        }
        request_body_encoded = json.dumps(request_body).encode("utf-8")
        req = func.HttpRequest(
            method="POST",
            body=request_body_encoded,
            url="/api/tests/test-id/progresses/3",
            route_params={"testId": "test-id", "questionNumber": "3"},
            headers={"X-User-Id": "user-id"},
        )
        res = post_progress(req)

        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.get_body().decode("utf-8"), "Internal Server Error")
        mock_validate_route_params.assert_called_once_with(req.route_params)
        mock_validate_headers.assert_called_once_with(req.headers)
        mock_validate_body.assert_called_once_with(request_body_encoded)
        mock_logging.info.assert_called_once_with(
            {"question_number": 3, "test_id": "test-id", "user_id": "user-id"}
        )
        mock_logging.error.assert_called_once()
