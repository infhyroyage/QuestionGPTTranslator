"""[DELETE] /tests/{testId}/progresses のモジュール"""

import logging
import traceback

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
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

        # 削除対象の回答履歴を削除
        container: ContainerProxy = get_read_write_container(
            database_name="Users",
            container_name="Progress",
        )
        try:
            container.delete_item(item=f"{user_id}_{test_id}", partition_key=test_id)
        except CosmosResourceNotFoundError:
            # 削除対象が存在しない場合でも200をレスポンスする
            pass

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
