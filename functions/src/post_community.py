"""[POST] /tests/{testId}/communities/{questionNumber} のモジュール"""

import json
import logging
import os
import traceback

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.storage.queue import BinaryBase64EncodePolicy, QueueClient
from openai import AzureOpenAI
from type.cosmos import Question, QuestionDiscussion
from type.message import MessageCommunity
from type.response import PostCommunityRes
from util.cosmos import get_read_only_container
from util.queue import AZURITE_QUEUE_STORAGE_CONNECTION_STRING

MAX_RETRY_NUMBER: int = 5
SYSTEM_PROMPT: str = (
    "You are a professional content summarizer who creates concise summaries "
    "of community discussions."
)


def calculate_community_votes(discussions: list[QuestionDiscussion]) -> list[str]:
    """
    コミュニティのディスカッションからユーザーが選択した選択肢を集計し、
    コミュニティでの回答の割合の文字列配列を生成する

    Args:
        discussions (list[QuestionDiscussion]): コミュニティのディスカッション

    Returns:
        list[str]: コミュニティでの回答の割合の文字列配列(例：["A (60%)", "B (40%)"]、ユーザーが選択した選択肢がすべてNoneの場合は空配列)
    """

    # ユーザーが選択した選択肢(selectedAnswer)を集計
    answer_counts = {}
    total_votes = 0
    for discussion in discussions:
        selected_answer = discussion.get("selectedAnswer")
        if selected_answer:
            answer_counts[selected_answer] = answer_counts.get(selected_answer, 0) + 1
            total_votes += 1

    if total_votes == 0:
        return []

    # 割合を計算してコミュニティでの回答の割合の文字列配列を生成
    community_votes = []
    for answer, count in sorted(answer_counts.items()):
        percentage = round((count / total_votes) * 100)
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


def create_discussion_summary_prompt(discussions: list[QuestionDiscussion]) -> str:
    """
    ディスカッション要約用のプロンプトを作成する

    Args:
        discussions (list[QuestionDiscussion]): ディスカッション情報のリスト

    Returns:
        str: 要約用のプロンプト
    """

    if not discussions:
        return "No community discussions available for this question."

    # ディスカッションの情報を整理
    discussion_content: list[str] = []
    for i, discussion in enumerate(discussions, 1):
        comment: str = discussion.get("comment")
        upvoted_num: int = discussion.get("upvotedNum")
        selected_answer: str | None = discussion.get("selectedAnswer")
        if selected_answer is None:
            selected_answer = "Not specified"

        discussion_content.append(
            f"Discussion {i}:\n"
            f"- Comment: {comment}\n"
            f"- Upvotes: {upvoted_num}\n"
            f"- Selected Answer: {selected_answer}"
        )

    # プロンプトを構築
    # pylint: disable=line-too-long
    prompt: str = f"""Please create a concise summary (approximately 200 characters) of the following \
community discussions about an exam question. Focus on the main points, popular opinions \
(based on upvotes), and the general consensus on answer choices.

Community Discussions:
{'\n\n'.join(discussion_content)}

Please provide a summary that captures:
1. The overall sentiment and main discussion points
2. Popular answer choices mentioned by users
3. Key insights or concerns raised by the community

Summary (approximately 200 characters):"""

    return prompt


def generate_discussion_summary(discussions: list[QuestionDiscussion]) -> str | None:
    """
    コミュニティディスカッションの要約を生成する

    Args:
        discussions (list[QuestionDiscussion]): ディスカッション情報のリスト

    Returns:
        str | None: 生成された要約文字列(生成できない場合はNone)
    """

    # プロンプトを作成
    prompt: str = create_discussion_summary_prompt(discussions)

    try:
        for retry_number in range(MAX_RETRY_NUMBER):
            logging.info({"retry_number": retry_number})

            # Azure OpenAIのチャット補完を実行
            response = AzureOpenAI(
                api_key=os.environ["OPENAI_API_KEY"],
                api_version=os.environ["OPENAI_API_VERSION"],
                azure_deployment=os.environ["OPENAI_DEPLOYMENT_NAME"],
                azure_endpoint=os.environ["OPENAI_ENDPOINT"],
            ).chat.completions.create(
                model=os.environ["OPENAI_MODEL_NAME"],
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                max_tokens=300,
                temperature=0.7,
            )
            logging.info({"content": response.choices[0].message.content})

            # レスポンスから要約文字列を取得
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()

    except Exception:
        logging.warning(traceback.format_exc())

    return None


def queue_message_community(message_community: MessageCommunity) -> None:
    """
    キューストレージにCommunityコンテナーの項目用のメッセージを格納する

    Args:
        message_community (MessageCommunity): Communityコンテナーの項目用のメッセージ
    """

    connection_string: str = os.environ["AzureWebJobsStorage"]
    if connection_string == "UseDevelopmentStorage=true":
        connection_string = AZURITE_QUEUE_STORAGE_CONNECTION_STRING

    queue_client = QueueClient.from_connection_string(
        conn_str=connection_string,
        queue_name="communities",
        message_encode_policy=BinaryBase64EncodePolicy(),
    )
    logging.info({"message_community": message_community})
    queue_client.send_message(json.dumps(message_community).encode("utf-8"))


bp_post_community = func.Blueprint()


@bp_post_community.route(
    route="tests/{testId}/communities/{questionNumber}",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
def post_community(req: func.HttpRequest) -> func.HttpResponse:
    """
    コミュニティディスカッションの要約を生成します
    """

    try:
        # バリデーションチェック
        error_message = validate_request(req)
        if error_message:
            return func.HttpResponse(body=error_message, status_code=400)

        test_id = req.route_params.get("testId")
        question_number = req.route_params.get("questionNumber")

        logging.info(
            {
                "question_number": question_number,
                "test_id": test_id,
            }
        )

        # Questionコンテナーの項目を取得
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

        # discussionsフィールドが存在する場合はディスカッション要約を生成(存在しない場合は空文字列)
        discussions: list[QuestionDiscussion] | None = item.get("discussions")
        body: PostCommunityRes = {
            "isExisted": False,
        }

        if discussions and len(discussions) > 0:
            # ディスカッション要約を生成
            summary: str | None = generate_discussion_summary(discussions)
            # コミュニティでの回答の割合を動的算出
            votes: list[str] = calculate_community_votes(discussions)
            if summary is None:
                raise ValueError("Failed to generate discussion summary")
            body["discussionsSummary"] = summary
            body["votes"] = votes
            body["isExisted"] = True

            # キューストレージにメッセージを格納
            queue_message_community(
                {
                    "testId": test_id,
                    "questionNumber": int(question_number),
                    "discussionsSummary": summary,
                    "votes": votes,
                }
            )

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
