"""[GET] /tests のテスト"""

import json
import os
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

import azure.functions as func
from src.get_tests import get_tests
from type.cosmos import Test
from type.response import GetTestsRes


class TestGetTests(TestCase):
    """get_tests関数のテストケース"""

    @patch("src.get_tests.get_read_only_container")
    @patch("src.get_tests.logging")
    @patch.dict(os.environ, {"COSMOSDB_URI": "https://localhost:8081"})
    def test_get_tests_success_local(self, mock_logging, mock_get_read_only_container):
        """ローカル環境でレスポンスが正常であることのテスト"""

        mock_container = MagicMock()
        mock_items: list[Test] = [
            {"id": "1", "courseName": "Math", "testName": "Algebra", "length": 10},
            {"id": "2", "courseName": "Math", "testName": "Geometry", "length": 20},
            {"id": "3", "courseName": "Science", "testName": "Physics", "length": 30},
        ]
        mock_container.query_items.return_value = mock_items
        mock_get_read_only_container.return_value = mock_container

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        response: func.HttpResponse = get_tests(req)

        self.assertEqual(response.status_code, 200)
        expected_body: GetTestsRes = {
            "Math": [
                {"id": "1", "testName": "Algebra", "length": 10},
                {"id": "2", "testName": "Geometry", "length": 20},
            ],
            "Science": [
                {"id": "3", "testName": "Physics", "length": 30},
            ],
        }
        self.assertEqual(response.get_body().decode(), json.dumps(expected_body))
        mock_container.query_items.assert_called_once_with(
            query="SELECT c.id, c.courseName, c.testName, c.length FROM c",
            enable_cross_partition_query=False,
        )
        mock_logging.info.assert_has_calls(
            [call({"items": mock_items}), call({"body": expected_body})]
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_tests.get_read_only_container")
    @patch("src.get_tests.logging")
    @patch.dict(
        os.environ, {"COSMOSDB_URI": "https://test-cosmosdb.documents.azure.com:443"}
    )
    def test_get_tests_success_azure(self, mock_logging, mock_get_read_only_container):
        """Azure環境でレスポンスが正常であることのテスト"""

        mock_container = MagicMock()
        mock_items: list[Test] = [
            {"id": "1", "courseName": "Math", "testName": "Algebra", "length": 10},
            {"id": "2", "courseName": "Math", "testName": "Geometry", "length": 20},
            {"id": "3", "courseName": "Science", "testName": "Physics", "length": 30},
        ]
        mock_container.query_items.return_value = mock_items
        mock_get_read_only_container.return_value = mock_container

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        response: func.HttpResponse = get_tests(req)

        self.assertEqual(response.status_code, 200)
        expected_body: GetTestsRes = {
            "Math": [
                {"id": "1", "testName": "Algebra", "length": 10},
                {"id": "2", "testName": "Geometry", "length": 20},
            ],
            "Science": [
                {"id": "3", "testName": "Physics", "length": 30},
            ],
        }
        self.assertEqual(response.get_body().decode(), json.dumps(expected_body))
        mock_container.query_items.assert_called_once_with(
            query=(
                "SELECT c.id, c.courseName, c.testName, c.length FROM c"
                " ORDER BY c.courseName ASC, c.testName ASC"
            ),
            enable_cross_partition_query=True,
        )
        mock_logging.info.assert_has_calls(
            [call({"items": mock_items}), call({"body": expected_body})]
        )
        mock_logging.error.assert_not_called()

    @patch("src.get_tests.get_read_only_container")
    @patch("src.get_tests.logging")
    def test_get_tests_exception(self, mock_logging, mock_get_read_only_container):
        """レスポンスが異常であることのテスト"""

        mock_get_read_only_container.side_effect = Exception(
            "Error in src.get_tests.get_read_only_container"
        )

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        response: func.HttpResponse = get_tests(req)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
        mock_logging.info.assert_not_called()
        mock_logging.error.assert_called_once()
