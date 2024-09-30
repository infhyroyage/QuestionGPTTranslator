"""[GET] /tests/{testId}/answers/{questionNumber} のモジュール"""

import json
import logging

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Answer
from type.response import GetAnswerRes
from util.cosmos import get_read_only_container

bp_get_answer = func.Blueprint()


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
        # パスパラメーターのバリデーションチェック
        test_id = req.route_params.get("testId")
        question_number = req.route_params.get("questionNumber")
        if test_id is None or question_number is None:
            raise ValueError(
                f"Invalid testId or questionNumber: {test_id}, {question_number}"
            )

        # Answerコンテナーの読み取り専用インスタンスを取得
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Answer",
        )

        # Answerコンテナーから項目取得
        items: list[Answer] = list(
            container.query_items(
                query="SELECT c.correctIdxes, c.explanations FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": f"{test_id}_{question_number}"}],
            )
        )
        logging.info({"items": items})

        # 項目数のチェック
        if len(items) == 0:
            return func.HttpResponse(body="Not Found Answer", status_code=404)
        if len(items) > 1:
            raise ValueError("Not Unique Answer")

        body: GetAnswerRes = items[0]
        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
