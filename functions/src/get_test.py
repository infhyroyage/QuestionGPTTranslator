"""[GET] /tests/{testId} のモジュール"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Test
from type.response import GetTestRes
from util.cosmos import get_read_only_container

bp_get_test = func.Blueprint()


@bp_get_test.route(
    route="tests/{testId}",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_test(req: func.HttpRequest) -> func.HttpResponse:
    """
    指定したテストIDでのテストの詳細情報を取得します
    """

    try:
        # パスパラメーターのバリデーションチェック
        test_id = req.route_params.get("testId")
        if test_id is None:
            raise ValueError(f"Invalid testId: {test_id}")

        # Testコンテナーの読み取り専用インスタンスを取得
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Test",
        )

        # Testコンテナーから項目取得
        items: list[Test] = list(
            container.query_items(
                query="SELECT c.id, c.courseName, c.testName, c.length FROM c WHERE c.id = @testId",
                parameters=[{"name": "@testId", "value": test_id}],
            )
        )
        logging.info({"items": items})

        # 項目数のチェック
        if len(items) == 0:
            return func.HttpResponse(body="Not Found Test", status_code=404)
        if len(items) > 1:
            raise ValueError("Not Unique Test")

        body: GetTestRes = items[0]
        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(body="Internal Server Error", status_code=500)
