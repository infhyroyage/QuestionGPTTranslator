"""[GET] /tests/{testId}/questions/{questionNumber} のテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from src.get_question import get_question, validate_request


class TestValidateRequest(TestCase):
    """validate_request関数のテストケース"""

    def test_validate_request_success(self):
        """バリデーションチェックに成功した場合のテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}
        result = validate_request(req)

        self.assertIsNone(result)

    def test_validate_request_test_id_empty(self):
        """testIdが空である場合のテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"questionNumber": "1"}

        result = validate_request(req)

        self.assertEqual(result, "testId is Empty")

    def test_validate_request_question_number_empty(self):
        """questionNumberが空である場合のテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}

        result = validate_request(req)

        self.assertEqual(result, "questionNumber is Empty")

    def test_validate_request_question_number_not_digit(self):
        """questionNumberが数値でない場合のテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "invalid"}

        result = validate_request(req)

        self.assertEqual(result, "Invalid questionNumber: invalid")


class TestGetQuestion(TestCase):
    """get_question関数のテストケース"""

    @patch("src.get_question.validate_request")
    @patch("src.get_question.get_read_only_container")
    @patch("src.get_question.logging")
    def test_get_question_success(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """回答が1個のみ存在する問題のレスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_item = {
            "subjects": ["What is the capital of France?"],
            "choices": ["Paris", "London", "Berlin"],
            "answerNum": 1,
            "indicateSubjectImgIdxes": [0],
            "indicateChoiceImgs": [None, None, None],
            "escapeTranslatedIdxes": {"subjects": [0], "choices": [1]},
        }
        mock_container.read_item.return_value = mock_item
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_question(req)

        self.assertEqual(response.status_code, 200)
        expected_body = {
            "subjects": [
                {
                    "sentence": "What is the capital of France?",
                    "isIndicatedImg": True,
                    "isEscapedTranslation": True,
                }
            ],
            "choices": [
                {
                    "sentence": "Paris",
                    "img": None,
                    "isEscapedTranslation": False,
                },
                {
                    "sentence": "London",
                    "img": None,
                    "isEscapedTranslation": True,
                },
                {
                    "sentence": "Berlin",
                    "img": None,
                    "isEscapedTranslation": False,
                },
            ],
            "isMultiplied": False,
        }
        self.assertEqual(json.loads(response.get_body().decode()), expected_body)
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        mock_logging.info.assert_has_calls(
            [call({"item": mock_item}), call({"body": expected_body})]
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_question.validate_request")
    @patch("src.get_question.get_read_only_container")
    @patch("src.get_question.logging")
    def test_get_question_success_with_multiple_answers(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """回答が複数個存在する問題のレスポンスが正常であることのテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_item = {
            "subjects": ["Select the two fruits."],
            "choices": ["Apple", "Car", "Banana", "House"],
            "answerNum": 2,
            "indicateSubjectImgIdxes": None,
            "indicateChoiceImgs": None,
            "escapeTranslatedIdxes": None,
        }
        mock_container.read_item.return_value = mock_item
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_question(req)

        self.assertEqual(response.status_code, 200)
        expected_body = {
            "subjects": [
                {
                    "sentence": "Select the two fruits.",
                    "isIndicatedImg": False,
                    "isEscapedTranslation": False,
                }
            ],
            "choices": [
                {
                    "sentence": "Apple",
                    "img": None,
                    "isEscapedTranslation": False,
                },
                {
                    "sentence": "Car",
                    "img": None,
                    "isEscapedTranslation": False,
                },
                {
                    "sentence": "Banana",
                    "img": None,
                    "isEscapedTranslation": False,
                },
                {
                    "sentence": "House",
                    "img": None,
                    "isEscapedTranslation": False,
                },
            ],
            "isMultiplied": True,
        }
        self.assertEqual(json.loads(response.get_body().decode()), expected_body)
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        mock_logging.info.assert_has_calls(
            [call({"item": mock_item}), call({"body": expected_body})]
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_question.validate_request")
    def test_get_question_validation_error(self, mock_validate_request):
        """バリデーションチェックに失敗した場合のテスト"""

        mock_validate_request.return_value = "Validation Error"
        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_question(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_body().decode(), "Validation Error")
        mock_validate_request.assert_called_once_with(req)

    @patch("src.get_question.validate_request")
    @patch("src.get_question.get_read_only_container")
    @patch("src.get_question.logging")
    def test_get_question_not_found(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """問題が見つからない場合のテスト"""

        mock_validate_request.return_value = None
        mock_container = MagicMock()
        mock_container.read_item.side_effect = CosmosResourceNotFoundError
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_question(req)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_body().decode(), "Not Found Question")
        mock_validate_request.assert_called_once_with(req)
        mock_get_read_only_container.assert_called_once_with(
            database_name="Users",
            container_name="Question",
        )
        mock_container.read_item.assert_called_once_with(
            item="1_1",
            partition_key="1",
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_question.validate_request")
    @patch("src.get_question.get_read_only_container")
    @patch("src.get_question.logging")
    def test_get_question_not_unique(
        self, mock_logging, mock_get_read_only_container, mock_validate_request
    ):
        """例外が発生した場合のテスト"""

        mock_validate_request.return_value = None
        mock_get_read_only_container.side_effect = Exception(
            "Error in src.get_question.get_read_only_container"
        )

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_question(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_validate_request.assert_called_once_with(req)
        mock_logging.error.assert_called_once()
