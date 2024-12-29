"""[GET] /tests/{testId} のテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

import azure.functions as func
from src.get_test import get_test
from type.cosmos import Test
from type.response import GetTestRes


class TestGetTest(TestCase):
    """[GET] /tests/{testId} のテストケース"""

    @patch("src.get_test.get_read_only_container")
    @patch("src.get_test.logging")
    def test_get_test_success(self, mock_logging, mock_get_read_only_container):
        """レスポンスが正常であることのテスト"""

        mock_container = MagicMock()
        mock_items: list[Test] = [
            {"id": "1", "courseName": "Math", "testName": "Algebra", "length": 10}
        ]
        mock_container.query_items.return_value = mock_items
        mock_get_read_only_container.return_value = mock_container

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}
        response: func.HttpResponse = get_test(req)

        self.assertEqual(response.status_code, 200)
        expected_body: GetTestRes = {
            "id": "1",
            "courseName": "Math",
            "testName": "Algebra",
            "length": 10,
        }
        self.assertEqual(response.get_body().decode(), json.dumps(expected_body))
        mock_logging.info.assert_called_once_with({"items": mock_items})
        mock_logging.error.assert_not_called()

    @patch("src.get_test.get_read_only_container")
    @patch("src.get_test.logging")
    def test_get_test_not_found(self, mock_logging, mock_get_read_only_container):
        """テストが見つからない場合のレスポンスのテスト"""

        mock_container = MagicMock()
        mock_container.query_items.return_value = []
        mock_get_read_only_container.return_value = mock_container

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}
        response: func.HttpResponse = get_test(req)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_body().decode(), "Not Found Test")
        mock_logging.info.assert_called_once_with({"items": []})
        mock_logging.error.assert_not_called()

    @patch("src.get_test.get_read_only_container")
    @patch("src.get_test.logging")
    def test_get_test_not_unique(self, mock_logging, mock_get_read_only_container):
        """テストが一意でない場合のレスポンスのテスト"""

        mock_container = MagicMock()
        mock_items: list[Test] = [
            {"id": "1", "courseName": "Math", "testName": "Algebra", "length": 10},
            {"id": "1", "courseName": "Math", "testName": "Geometry", "length": 20},
        ]
        mock_container.query_items.return_value = mock_items
        mock_get_read_only_container.return_value = mock_container

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}
        response: func.HttpResponse = get_test(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_logging.info.assert_called_once_with({"items": mock_items})
        mock_logging.error.assert_called_once()

    @patch("src.get_test.logging")
    def test_get_test_invalid_test_id(self, mock_logging):
        """testIdが空であるレスポンスのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {}
        response: func.HttpResponse = get_test(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()

    @patch("src.get_test.get_read_only_container")
    @patch("src.get_test.logging")
    def test_get_test_exception(self, mock_logging, mock_get_read_only_container):
        """レスポンスが異常であることのテスト"""

        mock_get_read_only_container.side_effect = Exception(
            "Error in src.get_test.get_read_only_container"
        )

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        req.route_params = {"testId": "1"}
        response: func.HttpResponse = get_test(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()
