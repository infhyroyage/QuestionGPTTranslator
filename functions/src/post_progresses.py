"""[POST] /tests/{testId}/progresses のモジュール"""

import json
import logging
import traceback

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from type.request import PostProgressesReq
from util.cosmos import get_read_write_container


def validate_body(req_body_encoded: bytes) -> list:
    """
    リクエストボディのバリデーションを行う

    Args:
        req_body_encoded (bytes): リクエストボディ

    Returns:
        list: バリデーションチェックに成功した場合は空のリスト、失敗した場合はエラーメッセージのリスト
    """

    errors = []

    if not req_body_encoded:
        errors.append("Request Body is Empty")
    else:
        req_body = json.loads(req_body_encoded.decode("utf-8"))

        if "order" not in req_body:
            errors.append("order is required")
        elif not isinstance(req_body["order"], list):
            errors.append(f"Invalid order: {req_body["order"]}")
        else:
            for i, item in enumerate(req_body["order"]):
                if item is not None and not isinstance(item, int):
                    errors.append(f"Invalid order[{i}]: {item}")

    return errors


def validate_route_params(route_params: dict) -> list:
    """
    ルートパラメータのバリデーションを行う

    Args:
        route_params (dict): ルートパラメータ

    Returns:
        list: バリデーションチェックに成功した場合は空のリスト、失敗した場合はエラーメッセージのリスト
    """

    errors = []

    test_id = route_params.get("testId")
    if not test_id:
        errors.append("testId is Empty")

    return errors


def validate_headers(headers: dict) -> list:
    """
    ヘッダーのバリデーションを行う

    Args:
        headers (dict): ヘッダー

    Returns:
        list: バリデーションチェックに成功した場合は空のリスト、失敗した場合はエラーメッセージのリスト
    """

    errors = []

    user_id = headers.get("X-User-Id")
    if not user_id:
        errors.append("X-User-Id header is Empty")

    return errors


bp_post_progresses = func.Blueprint()


@bp_post_progresses.route(
    route="tests/{testId}/progresses",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
def post_progresses(req: func.HttpRequest) -> func.HttpResponse:
    """
    指定したテストID・ユーザーIDでのテストを解く問題番号の順番を保存します
    """

    try:
        # バリデーションチェック
        errors = []
        req_body_encoded: bytes = req.get_body()
        errors.extend(validate_body(req_body_encoded))  # リクエストボディ
        errors.extend(validate_route_params(req.route_params))  # ルートパラメータ
        errors.extend(validate_headers(req.headers))  # ヘッダー
        error_message = errors[0] if errors else None
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

        # 既にテストを解く問題番号の順番を保存していないかのチェック
        try:
            container.read_item(item=f"{user_id}_{test_id}", partition_key=test_id)
            return func.HttpResponse(
                body="Progresses Order Already exists", status_code=400
            )
        except CosmosResourceNotFoundError:
            pass

        req_body: PostProgressesReq = json.loads(req_body_encoded.decode("utf-8"))

        # Progressの項目をupsert
        container.upsert_item(
            {
                "id": f"{user_id}_{test_id}",
                "userId": user_id,
                "testId": test_id,
                "order": req_body["order"],
                "progresses": [],
            }
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
