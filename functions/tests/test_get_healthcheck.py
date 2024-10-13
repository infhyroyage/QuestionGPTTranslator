"""[GET] /healthcheck のテスト"""

from unittest import TestCase
from unittest.mock import MagicMock

import azure.functions as func
from src.get_healthcheck import get_healthcheck


class TestGetHealthcheck(TestCase):
    """[GET] /healthcheck のテストケース"""

    def test_response(self):
        """レスポンスが正常であることのテスト"""

        req: func.HttpRequest = MagicMock(spec=func.HttpRequest)
        response: func.HttpResponse = get_healthcheck(req)

        # ステータスコード・レスポンスボディの確認
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_body().decode(), "OK")
