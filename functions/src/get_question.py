"""[GET] /tests/{testId}/questions/{questionNumber} のモジュール"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
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

        # Questionコンテナーの読み取り専用インスタンスを取得
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Question",
        )

        # Questionコンテナーから項目取得
        items: list[Question] = list(
            container.query_items(
                query=(
                    "SELECT c.subjects, c.choices, c.isMultiplied, c.indicateSubjectImgIdxes, "
                    "c.indicateChoiceImgs, c.escapeTranslatedIdxes "
                    "FROM c WHERE c.testId = @testId AND c.number = @number"
                ),
                parameters=[
                    {"name": "@testId", "value": test_id},
                    {"name": "@number", "value": int(question_number)},
                ],
            )
        )
        logging.info({"items": items})

        # 項目数のチェック
        if len(items) == 0:
            return func.HttpResponse(body="Not Found Question", status_code=404)
        if len(items) > 1:
            raise ValueError("Not Unique Question")
        result: Question = items[0]

        # レスポンス整形
        body: GetQuestionRes = {
            "subjects": [
                {
                    "sentence": subject,
                    "isIndicatedImg": bool(
                        result.get("indicateSubjectImgIdxes")
                        and idx in result["indicateSubjectImgIdxes"]
                    ),
                    "isEscapedTranslation": bool(
                        result.get("escapeTranslatedIdxes")
                        and result["escapeTranslatedIdxes"].get("subjects")
                        and idx in result["escapeTranslatedIdxes"]["subjects"]
                    ),
                }
                for idx, subject in enumerate(result["subjects"])
            ],
            "choices": [
                {
                    "sentence": choice,
                    "img": (
                        result.get("indicateChoiceImgs")[idx]
                        if result.get("indicateChoiceImgs")
                        else None
                    ),
                    "isEscapedTranslation": bool(
                        result.get("escapeTranslatedIdxes")
                        and result["escapeTranslatedIdxes"].get("choices")
                        and idx in result["escapeTranslatedIdxes"]["choices"]
                    ),
                }
                for idx, choice in enumerate(result["choices"])
            ],
            "isMultiplied": result["isMultiplied"],
        }
        logging.info({"body": body})

        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(body="Internal Server Error", status_code=500)
