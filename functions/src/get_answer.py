"""[GET] /tests/{testId}/answers/{questionNumber} のモジュール"""

import json
import logging
import traceback
from collections import Counter
from typing import List, Optional

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from type.cosmos import Answer, Question
from type.response import GetAnswerRes
from util.cosmos import get_read_only_container

bp_get_answer = func.Blueprint()


def calculate_community_votes(discussions: Optional[List[dict]]) -> Optional[List[str]]:
    """
    discussionsのselectedAnswerから動的にcommunityVotesを算出する

    Args:
        discussions: QuestionのdiscussionsフィールドのList

    Returns:
        communityVotes: 選択肢毎の割合のリスト
    """
    if not discussions:
        return None

    # selectedAnswerを収集（None以外）
    selected_answers = [
        discussion["selectedAnswer"]
        for discussion in discussions
        if discussion.get("selectedAnswer") is not None
    ]

    if not selected_answers:
        return None

    # 各選択肢の選択回数を集計
    answer_counts = Counter(selected_answers)
    total_count = len(selected_answers)

    # 割合を計算してcommunityVotesを生成
    community_votes = []
    for answer, count in answer_counts.items():
        percentage = round((count / total_count) * 100)
        community_votes.append(f"{answer} ({percentage}%)")

    return community_votes


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

        # Answerコンテナーの読み取り専用インスタンスを取得
        answer_container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Answer",
        )

        # Questionコンテナーの読み取り専用インスタンスを取得
        question_container: ContainerProxy = get_read_only_container(
            database_name="Users",
            container_name="Question",
        )

        try:
            # Answerコンテナーから項目取得
            answer_item: Answer = answer_container.read_item(
                item=f"{test_id}_{question_number}", partition_key=test_id
            )

            # Questionコンテナーから項目取得（discussionsを取得するため）
            question_item: Question = question_container.read_item(
                item=f"{test_id}_{question_number}", partition_key=test_id
            )

            logging.info({"answer_item": answer_item, "question_item": question_item})

            # discussionsからcommunityVotesを動的に算出
            community_votes = calculate_community_votes(question_item.get("discussions"))

            # レスポンス整形
            body: GetAnswerRes = {
                "correctIdxes": answer_item["correctIdxes"],
                "explanations": answer_item["explanations"],
                "isExisted": True,
            }
            if community_votes is not None:
                body["communityVotes"] = community_votes
            logging.info({"body": body})

            return func.HttpResponse(
                body=json.dumps(body),
                status_code=200,
                mimetype="application/json",
            )
        except CosmosResourceNotFoundError:
            # Answerコンテナーから項目を取得できない場合、
            # 正解の選択肢・正解/不正解の理由を除いてレスポンス
            body: GetAnswerRes = {
                "isExisted": False,
            }
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
