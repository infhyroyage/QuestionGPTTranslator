"""[GET] /tests/{testId}/favorites/{questionNumber} のモジュール"""

import json
import logging
import traceback

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from type.response import GetFavoriteRes
from util.cosmos import get_read_only_container


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

    return errors[0] if errors else None


bp_get_favorite = func.Blueprint()


@bp_get_favorite.route(
    route="tests/{testId}/favorites/{questionNumber}",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_favorite(req: func.HttpRequest) -> func.HttpResponse:
    """
    指定したテストID・問題番号・ユーザーIDでのお気に入り情報を取得します
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
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Favorite",
        )

        # Favoriteコンテナーから項目取得してレスポンス整形
        # 項目が見つからない場合は、isFavoriteをfalseとみなす
        try:
            item = container.read_item(
                item=f"{user_id}_{test_id}_{question_number}", partition_key=test_id
            )
            logging.info({"item": item})
            body: GetFavoriteRes = {"isFavorite": item["isFavorite"]}
        except CosmosResourceNotFoundError:
            body: GetFavoriteRes = {"isFavorite": False}

        logging.info({"body": body})

        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception:
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
