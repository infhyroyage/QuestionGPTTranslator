"""[POST] /tests/{testId}/progresses/{questionNumber} のモジュール"""

import json
import logging
import traceback
from typing import List

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.request import PostProgressReq
from util.cosmos import get_read_write_container


def _validate_list_field(field_name: str, field_value, expected_type=str) -> list:
    """リクエストボディ内のlist型のフィールドのバリデーションを行う

    Args:
        field_name (str): フィールド名
        field_value: フィールド値
        expected_type: 期待する型

    Returns:
        list: バリデーションチェックに成功した場合は空のリスト、失敗した場合はエラーメッセージのリスト
    """

    errors = []

    if not isinstance(field_value, list):
        errors.append(f"Invalid {field_name}: {field_value}")
    else:
        for i, item in enumerate(field_value):
            if item is not None and not isinstance(item, expected_type):
                errors.append(f"Invalid {field_name}[{i}]: {item}")

    return errors


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

        if "isCorrect" not in req_body:
            errors.append("isCorrect is required")
        elif not isinstance(req_body["isCorrect"], bool):
            errors.append(f"Invalid isCorrect: {req_body['isCorrect']}")

        list_fields = {
            "choiceSentences": str,
            "choiceImgs": None,
            "selectedIdxes": int,
            "correctIdxes": int,
        }
        for field, expected_type in list_fields.items():
            if field not in req_body:
                errors.append(f"{field} is required")
            else:
                if expected_type:
                    errors.extend(
                        _validate_list_field(field, req_body[field], expected_type)
                    )
                elif field == "choiceImgs":
                    errors.extend(_validate_list_field(field, req_body[field], str))

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

    question_number = route_params.get("questionNumber")
    if not question_number:
        errors.append("questionNumber is Empty")
    elif not question_number.isdigit():
        errors.append(f"Invalid questionNumber: {question_number}")

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


bp_post_progress = func.Blueprint()


@bp_post_progress.route(
    route="tests/{testId}/progresses/{questionNumber}",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
def post_progress(req: func.HttpRequest) -> func.HttpResponse:
    """
    指定したテストID・問題番号・ユーザーIDでの回答履歴を保存します
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
        question_number = int(req.route_params.get("questionNumber"))
        user_id = req.headers.get("X-User-Id")

        logging.info(
            {
                "question_number": question_number,
                "test_id": test_id,
                "user_id": user_id,
            }
        )

        # Progressコンテナーのインスタンスを取得
        container: ContainerProxy = get_read_write_container(
            database_name="Users",
            container_name="Progress",
        )

        # テストID・ユーザーIDにおける、最後に保存した回答履歴の問題番号、または次の問題番号であるかのチェック
        items: List[dict] = list(
            container.query_items(
                query=(
                    "SELECT MAX(c.questionNumber) as maxQuestionNumber "
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
        # 何も解答履歴を保存していない場合は、max_question_numberをNoneから0に変換
        max_question_number: int | None = items[0].get("maxQuestionNumber")
        if max_question_number is None:
            max_question_number = 0
        if question_number not in (max_question_number, max_question_number + 1):
            body = (
                f"questionNumber must be {max_question_number} or {max_question_number + 1}"
                if max_question_number > 0
                else f"questionNumber must be {max_question_number + 1}"
            )
            return func.HttpResponse(body=body, status_code=400)

        # Progressの項目を生成してupsert
        req_body: PostProgressReq = json.loads(req_body_encoded.decode("utf-8"))
        container.upsert_item(
            {
                "id": f"{user_id}_{test_id}_{question_number}",
                "userId": user_id,
                "testId": test_id,
                "questionNumber": question_number,
                "isCorrect": req_body.get("isCorrect"),
                "choiceSentences": req_body.get("choiceSentences"),
                "choiceImgs": req_body.get("choiceImgs"),
                "selectedIdxes": req_body.get("selectedIdxes"),
                "correctIdxes": req_body.get("correctIdxes"),
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
