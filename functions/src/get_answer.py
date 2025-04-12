"""[GET] /tests/{testId}/answers/{questionNumber} のモジュール"""

import json
import logging
import traceback

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from type.cosmos import Answer
from type.response import GetAnswerRes
from util.cosmos import get_read_only_container

bp_get_answer = func.Blueprint()


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

    return errors[0] if errors else None


@bp_get_answer.route(
    route="tests/{testId}/answers/{questionNumber}",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_answer(req: func.HttpRequest) -> func.HttpResponse:
    """
    指定したテストID・問題番号での正解の選択肢・正解/不正解の理由を取得します
    """

    try:
        # バリデーションチェック
        error_message = validate_request(req)
        if error_message:
            return func.HttpResponse(body=error_message, status_code=400)

        test_id = req.route_params.get("testId")
        question_number = req.route_params.get("questionNumber")

        # Answerコンテナーから項目取得
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Answer",
        )
        try:
            item: Answer = container.read_item(
                item=f"{test_id}_{question_number}", partition_key=test_id
            )
        except CosmosResourceNotFoundError:
            return func.HttpResponse(body="Not Found Answer", status_code=404)
        logging.info({"item": item})

        # レスポンス整形
        body: GetAnswerRes = {
            "correctIdxes": item["correctIdxes"],
            "explanations": item["explanations"],
            "communityVotes": item["communityVotes"],
        }
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
