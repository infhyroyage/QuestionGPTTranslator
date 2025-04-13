"""[DELETE] /tests/{testId}/progresses のモジュール"""

import logging
import traceback
from typing import Any, Dict, List, Tuple

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Progress
from util.cosmos import get_read_write_container


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


bp_delete_progresses = func.Blueprint()


@bp_delete_progresses.route(
    route="tests/{testId}/progresses",
    methods=["DELETE"],
    auth_level=func.AuthLevel.FUNCTION,
)
def delete_progresses(req: func.HttpRequest) -> func.HttpResponse:
    """
    指定したテストID・ユーザーIDに関連するすべての回答履歴を削除します
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

        # Progressコンテナーのインスタンスを取得
        container: ContainerProxy = get_read_write_container(
            database_name="Users",
            container_name="Progress",
        )

        # 削除対象の回答履歴を全取得
        items: List[Progress] = list(
            container.query_items(
                query=(
                    "SELECT c.id "
                    "FROM c WHERE c.userId = @userId AND c.testId = @testId"
                ),
                parameters=[
                    {"name": "@userId", "value": user_id},
                    {"name": "@testId", "value": test_id},
                ],
                partition_key=test_id,
            )
        )
        logging.info({"items": items})

        # 削除対象の回答履歴が存在しない場合は、何もせず正常終了
        if len(items) == 0:
            return func.HttpResponse(
                body="OK",
                status_code=200,
            )

        # 削除対象の回答履歴を一括削除
        batch_operations: List[Tuple[str, Tuple[str, ...], Dict[str, Any]]] = [
            ("delete", (item["id"],), {}) for item in items
        ]
        container.execute_item_batch(
            batch_operations=batch_operations, partition_key=test_id
        )

        return func.HttpResponse(
            body="OK",
            status_code=200,
        )
    except Exception:
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
