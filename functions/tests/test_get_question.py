"""[GET] /tests/{testId}/questions/{questionNumber} のテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

import azure.functions as func
from src.get_question import get_question


class TestGetQuestion(TestCase):
    """[GET] /tests/{testId}/questions/{questionNumber} のテストケース"""

    @patch("src.get_question.get_read_only_container")
    def test_get_question_success(self, mock_get_read_only_container):
        """レスポンスが正常であることのテスト"""

        mock_container = MagicMock()
        mock_items = [
            {
                "subjects": ["What is the capital of France?"],
                "choices": ["Paris", "London", "Berlin"],
                "isMultiplied": False,
                "indicateSubjectImgIdxes": [0],
                "indicateChoiceImgs": [None, None, None],
                "escapeTranslatedIdxes": {"subjects": [0], "choices": [1]},
            }
        ]
        mock_container.query_items.return_value = mock_items
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

    def test_get_question_test_id_empty(self):
        """testIdが空であるレスポンスのテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"questionNumber": "1"}

        response = get_question(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_body().decode(), "testId is empty")

    def test_get_question_question_number_empty(self):
        """questionNumberが空であるレスポンスのテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}

        response = get_question(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_body().decode(), "questionNumber is empty")

    def test_get_question_invalid_params(self):
        """questionNumberが無効であるレスポンスのテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "invalid"}

        response = get_question(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_body().decode(), "Invalid questionNumber: invalid"
        )

    @patch("src.get_question.get_read_only_container")
    def test_get_question_not_found(self, mock_get_read_only_container):
        """問題が見つからないレスポンスのテスト"""

        mock_container = MagicMock()
        mock_container.query_items.return_value = []
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_question(req)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_body().decode(), "Not Found Question")

    @patch("src.get_question.get_read_only_container")
    def test_get_question_not_unique(self, mock_get_read_only_container):
        """問題が一意に取得できないレスポンスのテスト"""

        mock_container = MagicMock()
        mock_container.query_items.return_value = [
            {},
            {},
        ]
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_question(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
