"""[POST] /tests/{testId}/progresses/{questionNumber} のモジュール"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.request import PostProgressReq
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

        if "isCorrect" not in req_body:
            errors.append("isCorrect is required")
        elif not isinstance(req_body["isCorrect"], bool):
            errors.append(f"Invalid isCorrect: {req_body['isCorrect']}")

        if "choiceSentences" not in req_body:
            errors.append("choiceSentences is required")
        elif not isinstance(req_body["choiceSentences"], list):
            errors.append(f"Invalid choiceSentences: {req_body['choiceSentences']}")
        else:
            for i, sentence in enumerate(req_body["choiceSentences"]):
                if not isinstance(sentence, str):
                    errors.append(f"Invalid choiceSentences[{i}]: {sentence}")

        if "choiceImgs" not in req_body:
            errors.append("choiceImgs is required")
        elif not isinstance(req_body["choiceImgs"], list):
            errors.append(f"Invalid choiceImgs: {req_body['choiceImgs']}")
        else:
            for i, img in enumerate(req_body["choiceImgs"]):
                if img is not None and not isinstance(img, str):
                    errors.append(f"Invalid choiceImgs[{i}]: {img}")

        if (
            "choiceTranslations" in req_body
            and req_body["choiceTranslations"] is not None
        ):
            if not isinstance(req_body["choiceTranslations"], list):
                errors.append(
                    f"Invalid choiceTranslations: {req_body['choiceTranslations']}"
                )
            else:
                for i, translation in enumerate(req_body["choiceTranslations"]):
                    if not isinstance(translation, str):
                        errors.append(f"Invalid choiceTranslations[{i}]: {translation}")

        if "selectedIdxes" not in req_body:
            errors.append("selectedIdxes is required")
        elif not isinstance(req_body["selectedIdxes"], list):
            errors.append(f"Invalid selectedIdxes: {req_body['selectedIdxes']}")
        else:
            for i, idx in enumerate(req_body["selectedIdxes"]):
                if not isinstance(idx, int):
                    errors.append(f"Invalid selectedIdxes[{i}]: {idx}")

        if "correctIdxes" not in req_body:
            errors.append("correctIdxes is required")
        elif not isinstance(req_body["correctIdxes"], list):
            errors.append(f"Invalid correctIdxes: {req_body['correctIdxes']}")
        else:
            for i, idx in enumerate(req_body["correctIdxes"]):
                if not isinstance(idx, int):
                    errors.append(f"Invalid correctIdxes[{i}]: {idx}")

    return errors[0] if errors else None


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

        # Progressコンテナーのインスタンスを取得
        container: ContainerProxy = get_read_write_container(
            database_name="Users",
            container_name="Progress",
        )

        # Progressの項目を生成してupsert
        req_body: PostProgressReq = json.loads(req.get_body().decode("utf-8"))
        container.upsert_item(
            body={
                "userId": user_id,
                "testId": test_id,
                "questionNumber": question_number,
                "isCorrect": req_body.get("isCorrect"),
                "choiceSentences": req_body.get("choiceSentences"),
                "choiceImgs": req_body.get("choiceImgs"),
                "choiceTranslations": req_body.get("choiceTranslations"),
                "selectedIdxes": req_body.get("selectedIdxes"),
                "correctIdxes": req_body.get("correctIdxes"),
            }
        )

        return func.HttpResponse(
            body="OK",
            status_code=200,
        )
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
