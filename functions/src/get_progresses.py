"""[GET] /tests/{testId}/progresses のモジュール"""

import json
import logging
import traceback

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from type.cosmos import Progress
from type.response import GetProgressesRes
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

        # Progressコンテナーから項目取得
        try:
            item: Progress = container.read_item(
                item=f"{user_id}_{test_id}", partition_key=test_id
            )
        except CosmosResourceNotFoundError:
            return func.HttpResponse(body="Not Found Progress", status_code=404)
        logging.info({"item": item})

        # レスポンス整形
        body: GetProgressesRes = [
            {
                "isCorrect": progress["isCorrect"],
                "choiceSentences": progress["choiceSentences"],
                "choiceImgs": progress["choiceImgs"],
                "selectedIdxes": progress["selectedIdxes"],
                "correctIdxes": progress["correctIdxes"],
            }
            for progress in item["progresses"]
        ]
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
