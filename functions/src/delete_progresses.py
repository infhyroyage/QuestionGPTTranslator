"""[DELETE] /tests/{testId}/progresses のモジュール"""

import logging
from typing import List

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosHttpResponseError
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


def chunk_list(items: List, chunk_size: int = 50):
    """
    リストを指定サイズのチャンクに分割する

    Args:
        items (List): 分割対象のリスト
        chunk_size (int): チャンクサイズ

    Yields:
        List: 分割されたチャンク
    """
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


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

        # テストID・ユーザーIDにおける、すべての回答履歴を取得
        items = list(
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
        if len(items) == 0:
            return func.HttpResponse(
                body="OK",
                status_code=200,
            )

        # 複数の項目を効率的に削除（チャンク単位で処理）
        try:
            # 30個程度のアイテムなので、1回の処理で十分だが、
            # スケーラビリティを考慮してチャンク処理を実装
            for chunk in chunk_list(items, 50):
                # ストアドプロシージャやバッチ操作が使用できない場合、
                # バルク処理として複数のdelete_itemを順次実行
                for item in chunk:
                    container.delete_item(item=item["id"], partition_key=test_id)

            return func.HttpResponse(
                body="OK",
                status_code=200,
            )
        except CosmosHttpResponseError as e:
            logging.error("Deletion failed: %s", e)
            raise
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
