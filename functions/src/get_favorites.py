"""[GET] /tests/{testId}/favorites のモジュール"""

import json
import logging
import traceback

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Favorite
from type.response import GetFavoritesRes
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

    user_id = req.headers.get("X-User-Id")
    if not user_id:
        errors.append("X-User-Id header is Empty")

    return errors[0] if errors else None


bp_get_favorites = func.Blueprint()


@bp_get_favorites.route(
    route="tests/{testId}/favorites",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_favorites(req: func.HttpRequest) -> func.HttpResponse:
    """
    指定したテストID・ユーザーIDでのすべての問題番号におけるお気に入り情報を取得します
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

        # Favoriteコンテナーのインスタンスを取得
        favorite_container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Favorite",
        )

        # Favoriteコンテナーから項目取得
        favorite_items: list[Favorite] = list(
            favorite_container.query_items(
                query=f"SELECT * FROM c WHERE c.userId = '{user_id}' AND c.testId = '{test_id}'",
                partition_key=test_id,
            )
        )

        # レスポンス整形
        body: GetFavoritesRes = [
            {
                "questionNumber": item["questionNumber"],
                "isFavorite": item["isFavorite"],
            }
            for item in favorite_items
        ]

        return func.HttpResponse(
            body=json.dumps(body),
            mimetype="application/json",
            status_code=200,
        )
    except Exception:
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
