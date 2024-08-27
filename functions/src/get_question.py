"""
Module of [GET] /tests/{testId}/questions/{questionNumber}
"""

import json
import logging
import re

import azure.functions as func
from azure.cosmos import ContainerProxy
from type.cosmos import Question
from type.response import GetQuestionRes
from util.cosmos import get_read_only_container

bp_get_question = func.Blueprint()


@bp_get_question.route(
    route="tests/{testId}/questions/{questionNumber}",
    methods=["GET"],
    auth_level=func.AuthLevel.FUNCTION,
)
def get_question(req: func.HttpRequest) -> func.HttpResponse:
    """
    Retrieve Question
    """

    try:
        # Validate Path Parameters
        test_id = req.route_params.get("testId")
        question_number = req.route_params.get("questionNumber")
        if test_id is None or question_number is None:
            raise ValueError(
                f"Invalid testId or questionNumber: {test_id}, {question_number}"
            )
        if not question_number.isdigit():
            return func.HttpResponse(
                body=f"Invalid questionNumber: {question_number}", status_code=400
            )

        # Initialize Cosmos DB Client
        container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Question",
        )

        # Execute Query
        query = (
            "SELECT c.subjects, c.choices, c.communityVotes, c.indicateSubjectImgIdxes, "
            "c.indicateChoiceImgs, c.escapeTranslatedIdxes "
            "FROM c WHERE c.testId = @testId AND c.number = @number"
        )
        parameters = [
            {"name": "@testId", "value": test_id},
            {"name": "@number", "value": int(question_number)},
        ]
        items: list[Question] = list(
            container.query_items(query=query, parameters=parameters)
        )
        logging.info({"items": items})

        if len(items) == 0:
            return func.HttpResponse(body="Not Found Question", status_code=404)
        if len(items) > 1:
            raise ValueError("Not Unique Question")
        result: Question = items[0]

        # communityVotesの最初の要素が「AB (100%)」のような形式の場合は回答が複数個、
        # 「A (100%)」のような形式の場合は回答が1個のみ存在すると判定
        is_multiplied: bool = bool(
            re.match(r"^[A-Z]{2,} \(\d+%\)$", result["communityVotes"][0])
        )

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
                    "img": result.get("indicateChoiceImgs", [None])[idx],
                    "isEscapedTranslation": bool(
                        result.get("escapeTranslatedIdxes")
                        and result["escapeTranslatedIdxes"].get("choices")
                        and idx in result["escapeTranslatedIdxes"]["choices"]
                    ),
                }
                for idx, choice in enumerate(result["choices"])
            ],
            "isMultiplied": is_multiplied,
        }
        logging.info({"body": body})

        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as e:  # pylint: disable=broad-except
        logging.error(e)
        return func.HttpResponse(body="Internal Server Error", status_code=500)
