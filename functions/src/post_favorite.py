"""[POST] /tests/{testId}/favorites/{questionNumber} のモジュール"""

import json
import logging
import traceback

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.request import PostFavoriteReq
from util.cosmos import get_read_write_container


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

    question_number = req.route_params.get("questionNumber")
    if not question_number:
        errors.append("questionNumber is Empty")
    elif not question_number.isdigit():
        errors.append(f"Invalid questionNumber: {question_number}")

    user_id = req.headers.get("X-User-Id")
    if not user_id:
        errors.append("X-User-Id header is Empty")

    req_body_encoded: bytes = req.get_body()
    if not req_body_encoded:
        errors.append("Request Body is Empty")
    else:
        req_body = json.loads(req_body_encoded.decode("utf-8"))

        if "isFavorite" not in req_body:
            errors.append("isFavorite is required")
        elif not isinstance(req_body["isFavorite"], bool):
            errors.append(f"Invalid isFavorite: {req_body['isFavorite']}")

    return errors[0] if errors else None


bp_post_favorite = func.Blueprint()


@bp_post_favorite.route(
    route="tests/{testId}/favorites/{questionNumber}",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
def post_favorite(req: func.HttpRequest) -> func.HttpResponse:
    """
    指定したテストID・問題番号・ユーザーIDでのお気に入り情報を保存します
    """

    try:
        # バリデーションチェック
        error_message = validate_request(req)
        if error_message:
            return func.HttpResponse(body=error_message, status_code=400)

        test_id = req.route_params.get("testId")
        question_number = int(req.route_params.get("questionNumber"))
        user_id = req.headers.get("X-User-Id")

        logging.info(
            {
                "question_number": question_number,
                "test_id": test_id,
                "user_id": user_id,
            }
        )

        # Favoriteコンテナーのインスタンスを取得
        container: ContainerProxy = get_read_write_container(
            database_name="Users",
            container_name="Favorite",
        )

        req_body: PostFavoriteReq = json.loads(req.get_body().decode("utf-8"))

        # Favoriteの項目をupsert
        container.upsert_item(
            {
                "id": f"{user_id}_{test_id}_{question_number}",
                "userId": user_id,
                "testId": test_id,
                "questionNumber": question_number,
                "isFavorite": req_body.get("isFavorite"),
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
