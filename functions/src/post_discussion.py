"""[POST] /tests/{testId}/discussions/{questionNumber} のモジュール"""

import logging
import os
import traceback

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from openai import AzureOpenAI
from type.cosmos import Question
from type.message import MessageDiscussion
from util.cosmos import get_read_only_container

MAX_RETRY_NUMBER: int = 5
SYSTEM_PROMPT: str = (
    "You are a professional content summarizer who creates concise summaries "
    "of community discussions."
)


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


def create_discussion_summary_prompt(discussions: list[dict]) -> str:
    """
    ディスカッション要約用のプロンプトを作成する

    Args:
        discussions (list[dict]): ディスカッション情報のリスト

    Returns:
        str: 要約用のプロンプト
    """

    if not discussions:
        return "No community discussions available for this question."

    # ディスカッションの情報を整理
    discussion_content = []
    for i, discussion in enumerate(discussions, 1):
        comment = discussion.get("comment", "")
        upvoted_num = discussion.get("upvotedNum", 0)
        selected_answer = discussion.get("selectedAnswer")
        if selected_answer is None:
            selected_answer = "Not specified"

        discussion_content.append(
            f"Discussion {i}:\n"
            f"- Comment: {comment}\n"
            f"- Upvotes: {upvoted_num}\n"
            f"- Selected Answer: {selected_answer}"
        )

    # プロンプトを構築
    prompt = f"""Please create a concise summary (approximately 200 characters) of the following \
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


def generate_discussion_summary(discussions: list[dict]) -> str | None:
    """
    コミュニティディスカッションの要約を生成する

    Args:
        discussions (list[dict]): ディスカッション情報のリスト

    Returns:
        str | None: 生成された要約文字列（生成できない場合はNone）
    """

    # プロンプトを作成
    prompt = create_discussion_summary_prompt(discussions)

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

            # レスポンスから要約文字列を取得
            if response.choices and response.choices[0].message.content:
                summary = response.choices[0].message.content.strip()
                logging.info({"generated_summary": summary})
                return summary

    except Exception:
        logging.warning(traceback.format_exc())

    return None


def queue_message_discussion(
    message_discussion: MessageDiscussion,  # pylint: disable=W0613
) -> None:
    """
    キューストレージにDiscussionコンテナーの項目用のメッセージを格納する
    TODO: 未実装

    Args:
        message_discussion (MessageDiscussion): Discussionコンテナーの項目用のメッセージ
    """

    pass  # pylint: disable=W0107


bp_post_discussion = func.Blueprint()


@bp_post_discussion.route(
    route="tests/{testId}/discussions/{questionNumber}",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
def post_discussion(req: func.HttpRequest) -> func.HttpResponse:
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
        discussions = item.get("discussions")
        summary = ""
        if discussions:
            summary = generate_discussion_summary(discussions)
            if summary is None:
                raise ValueError("Failed to generate discussion summary")

            # キューストレージにメッセージを格納
            message_discussion: MessageDiscussion = {
                "testId": test_id,
                "questionNumber": int(question_number),
                "summary": summary,
            }
            queue_message_discussion(message_discussion)

        return func.HttpResponse(
            body=summary,
            status_code=200,
            mimetype="text/plain",
        )

    except Exception:
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
