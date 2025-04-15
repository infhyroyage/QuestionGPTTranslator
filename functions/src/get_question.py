"""[GET] /tests/{testId}/questions/{questionNumber} のモジュール"""

import json
import logging
import traceback

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from type.cosmos import Question
from type.response import GetQuestionRes
from util.cosmos import get_read_only_container

bp_get_question = func.Blueprint()


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


@bp_get_question.route(
    route="tests/{testId}/questions/{questionNumber}",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_question(req: func.HttpRequest) -> func.HttpResponse:
    """
    指定したテストID・問題番号での問題・選択肢を取得します
    """

    try:
        # バリデーションチェック
        error_message = validate_request(req)
        if error_message:
            return func.HttpResponse(body=error_message, status_code=400)

        test_id = req.route_params.get("testId")
        question_number = req.route_params.get("questionNumber")

        # Questionコンテナーから項目取得
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Question",
        )
        try:
            item: Question = container.read_item(
                item=f"{test_id}_{question_number}", partition_key=test_id
            )
            logging.info({"item": item})
        except CosmosResourceNotFoundError:
            return func.HttpResponse(body="Not Found Question", status_code=404)

        # レスポンス整形
        body: GetQuestionRes = {
            "subjects": [
                {
                    "sentence": subject,
                    "isIndicatedImg": bool(
                        item.get("indicateSubjectImgIdxes")
                        and idx in item["indicateSubjectImgIdxes"]
                    ),
                    "isEscapedTranslation": bool(
                        item.get("escapeTranslatedIdxes")
                        and item["escapeTranslatedIdxes"].get("subjects")
                        and idx in item["escapeTranslatedIdxes"]["subjects"]
                    ),
                }
                for idx, subject in enumerate(item["subjects"])
            ],
            "choices": [
                {
                    "sentence": choice,
                    "img": (
                        item.get("indicateChoiceImgs")[idx]
                        if item.get("indicateChoiceImgs")
                        else None
                    ),
                    "isEscapedTranslation": bool(
                        item.get("escapeTranslatedIdxes")
                        and item["escapeTranslatedIdxes"].get("choices")
                        and idx in item["escapeTranslatedIdxes"]["choices"]
                    ),
                }
                for idx, choice in enumerate(item["choices"])
            ],
            "isMultiplied": item["isMultiplied"],
        }
        logging.info({"body": body})

        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception:
        logging.error(traceback.format_exc())
        return func.HttpResponse(body="Internal Server Error", status_code=500)
