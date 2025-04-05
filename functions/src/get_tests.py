"""[GET] /tests のモジュール"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Test
from type.response import GetTestsRes
from util.cosmos import get_read_only_container

bp_get_tests = func.Blueprint()


@bp_get_tests.route(
    route="tests",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_tests(
    req: func.HttpRequest,  # pylint: disable=unused-argument
) -> func.HttpResponse:
    """
    各コースに属するテストをすべて取得します
    """

    try:
        # Testコンテナーの読み取り専用インスタンスを取得
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Test",
        )

        # Testコンテナーから全項目取得
        items: list[Test] = list(container.read_all_items())
        logging.info({"items": items})

        # 各項目をcourseName単位でまとめるようにレスポンス整形
        body: GetTestsRes = {}
        for item in items:
            tmp_item = {
                "id": item["id"],
                "testName": item["testName"],
                "length": item["length"],
            }
            if item["courseName"] in body:
                body[item["courseName"]].append(tmp_item)
            else:
                body[item["courseName"]] = [tmp_item]
        logging.info({"body": body})

        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(body="Internal Server Error", status_code=500)
