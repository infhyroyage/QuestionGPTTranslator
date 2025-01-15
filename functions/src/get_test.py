"""[GET] /tests/{testId} のモジュール"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Test
from type.response import GetTestRes
from util.cosmos import get_read_only_container

bp_get_test = func.Blueprint()


def validate_request(req: func.HttpRequest) -> str | None:
    """
    リクエストのバリデーションチェックを行う

    Args:
        req (func.HttpRequest): リクエスト

    Returns:
        str | None: バリデーションチェックに成功した場合はNone、失敗した場合はエラーメッセージ
    """

    errors = []

    test_id = req.route_params.get("testId")
    if not test_id:
        errors.append("testId is Empty")

    return errors[0] if errors else None


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
        # バリデーションチェック
        error_message = validate_request(req)
        if error_message:
            return func.HttpResponse(body=error_message, status_code=400)

        test_id = req.route_params.get("testId")

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

        body: GetTestRes = {
            "courseName": items[0]["courseName"],
            "testName": items[0]["testName"],
            "length": items[0]["length"],
        }
        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(body="Internal Server Error", status_code=500)
