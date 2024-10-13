"""[GET] /tests のテスト"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

import azure.functions as func
from src.get_tests import get_tests
from type.cosmos import Test
from type.response import GetTestsRes


class TestGetTests(TestCase):
    """[GET] /tests のテストケース"""

    @patch("src.get_tests.get_read_only_container")
    def test_get_tests_success(self, mock_get_read_only_container):
        """レスポンスが正常であることのテスト"""

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

        # ステータスコードとレスポンスボディの確認
        self.assertEqual(response.status_code, 200)
        expected_body: GetTestsRes = {
            "Math": [
                {"id": "1", "testName": "Algebra"},
                {"id": "2", "testName": "Geometry"},
            ],
            "Science": [
                {"id": "3", "testName": "Physics"},
            ],
        }
        self.assertEqual(response.get_body().decode(), json.dumps(expected_body))

    @patch("src.get_tests.get_read_only_container")
    def test_get_tests_exception(self, mock_get_read_only_container):
        """レスポンスが異常であることのテスト"""

        mock_get_read_only_container.side_effect = Exception(
            "Error in src.get_tests.get_read_only_container"
        )

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        response: func.HttpResponse = get_tests(req)

        # ステータスコードとレスポンスボディの確認
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_body().decode(), "Internal Server Error")
