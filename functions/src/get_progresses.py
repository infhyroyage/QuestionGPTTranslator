"""[GET] /tests/{testId}/progresses のモジュール"""

import json
import logging
from typing import List

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Progress
from util.cosmos import get_read_only_container


def validate_request(req: func.HttpRequest) -> str | None:
    """
    リクエストのバリデーションチェックを行う

    Args:
        req (func.HttpRequest): HTTPリクエスト

    Returns:
        str | None: バリデーションチェックに成功した場合はNone、失敗した場合はエラーメッセージ
    """

    errors = []

    # ルートパラメータのバリデーション
    test_id = req.route_params.get("testId")
    if not test_id:
        errors.append("testId is Empty")

    # ヘッダーのバリデーション
    user_id = req.headers.get("X-User-Id")
    if not user_id:
        errors.append("X-User-Id header is Empty")

    return errors[0] if errors else None


bp_get_progresses = func.Blueprint()


@bp_get_progresses.route(
    route="tests/{testId}/progresses",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_progresses(req: func.HttpRequest) -> func.HttpResponse:
    """
    指定したテストID・ユーザーIDに対する、すべての問題番号での進捗項目を取得します
    """

    try:
        # バリデーションチェック
        error_message = validate_request(req)
        if error_message:
            return func.HttpResponse(body=error_message, status_code=400)

        test_id = req.route_params.get("testId")
        user_id = req.headers.get("X-User-Id")

        logging.info(
            {
                "test_id": test_id,
                "user_id": user_id,
            }
        )

        # Progressコンテナーの読み取り専用インスタンスを取得
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Progress",
        )

        # 指定されたテストIDとユーザーIDに関連する全ての進捗項目を取得
        items: List[Progress] = list(
            container.query_items(
                query=(
                    "SELECT * FROM c WHERE c.userId = @userId AND c.testId = @testId "
                    "ORDER BY c.questionNumber"
                ),
                parameters=[
                    {"name": "@userId", "value": user_id},
                    {"name": "@testId", "value": test_id},
                ],
                partition_key=test_id,
            )
        )
        logging.info({"items_count": len(items)})

        return func.HttpResponse(
            body=json.dumps(items),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
