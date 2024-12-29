"""[GET] /tests/{testId}/answers/{questionNumber} のテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

import azure.functions as func
from src.get_answer import get_answer


class TestGetAnswer(TestCase):
    """[GET] /tests/{testId}/answers/{questionNumber} のテストケース"""

    @patch("src.get_answer.get_read_only_container")
    @patch("src.get_answer.logging")
    def test_get_answer_success(self, mock_logging, mock_get_read_only_container):
        """レスポンスが正常であることのテスト"""

        mock_container = MagicMock()
        mock_items = [
            {
                "correctIdxes": [1],
                "explanations": ["Option 1 is correct because..."],
            }
        ]
        mock_container.query_items.return_value = mock_items
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 200)
        expected_body = {
            "correctIdxes": [1],
            "explanations": ["Option 1 is correct because..."],
        }
        self.assertEqual(json.loads(response.get_body().decode()), expected_body)
        mock_logging.info.assert_called_once_with({"items": [expected_body]})
        mock_logging.error.assert_not_called()

    @patch("src.get_answer.logging")
    def test_get_answer_test_id_empty(self, mock_logging):
        """testIdが空であるレスポンスのテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()

    @patch("src.get_answer.logging")
    def test_get_answer_question_number_empty(self, mock_logging):
        """questionNumberが空であるレスポンスのテスト"""

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()

    @patch("src.get_answer.get_read_only_container")
    @patch("src.get_answer.logging")
    def test_get_answer_not_found(self, mock_logging, mock_get_read_only_container):
        """回答が見つからない場合のレスポンスのテスト"""

        mock_container = MagicMock()
        mock_container.query_items.return_value = []
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_body().decode(), "Not Found Answer")
        mock_logging.info.assert_called_once_with({"items": []})
        mock_logging.error.assert_not_called()

    @patch("src.get_answer.get_read_only_container")
    @patch("src.get_answer.logging")
    def test_get_answer_not_unique(self, mock_logging, mock_get_read_only_container):
        """回答が一意でない場合のレスポンスのテスト"""

        mock_container = MagicMock()
        mock_container.query_items.return_value = [
            {"correctIdxes": [1], "explanations": ["Option 1 is correct because..."]},
            {"correctIdxes": [2], "explanations": ["Option 2 is correct because..."]},
        ]
        mock_get_read_only_container.return_value = mock_container

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_logging.info.assert_called_once_with(
            {
                "items": [
                    {
                        "correctIdxes": [1],
                        "explanations": ["Option 1 is correct because..."],
                    },
                    {
                        "correctIdxes": [2],
                        "explanations": ["Option 2 is correct because..."],
                    },
                ]
            }
        )
        mock_logging.error.assert_called_once()

    @patch("src.get_answer.get_read_only_container")
    @patch("src.get_answer.logging")
    def test_get_answer_exception(self, mock_logging, mock_get_read_only_container):
        """例外が発生した場合のレスポンスのテスト"""

        mock_get_read_only_container.side_effect = Exception(
            "Error in src.get_test.get_read_only_container"
        )

        req = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1", "questionNumber": "1"}

        response = get_answer(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()
