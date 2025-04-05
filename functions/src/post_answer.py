"""[POST] /tests/{testId}/answers/{questionNumber} のモジュール"""

import json
import logging
import os
from typing import Iterable

import azure.functions as func
from azure.cosmos import ContainerProxy
from azure.storage.queue import BinaryBase64EncodePolicy, QueueClient
from openai import AzureOpenAI
from openai.types.chat.chat_completion_content_part_param import (
    ChatCompletionContentPartParam,
)
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from type.cosmos import Question
from type.message import MessageAnswer
from type.openai import CorrectAnswers
from type.response import PostAnswerRes
from type.structured import AnswerFormat
from util.cosmos import get_read_only_container
from util.queue import AZURITE_QUEUE_STORAGE_CONNECTION_STRING

MAX_RETRY_NUMBER: int = 5
SYSTEM_PROMPT: str = (
    "You are a professional who provides correct explanations for candidates of the exam."
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


def get_question_items(test_id: str, question_number: str) -> list[Question]:
    """
    テストIDと問題番号から、Questionコンテナーの項目を取得する

    Args:
        test_id (str): テストID
        question_number (str): 問題番号

    Returns:
        list[Question]: Questionコンテナーの項目のリスト
    """

    # Questionコンテナーの読み取り専用インスタンスを取得
    container: ContainerProxy = get_read_only_container(
        database_name="Users",
        container_name="Question",
    )

    # Questionコンテナーから項目取得
    return list(
        container.query_items(
            query=(
                "SELECT c.subjects, c.choices, c.indicateSubjectImgIdxes, "
                "c.indicateChoiceImgs, c.communityVotes "
                "FROM c WHERE c.testId = @testId AND c.number = @number"
            ),
            parameters=[
                {"name": "@testId", "value": test_id},
                {"name": "@number", "value": int(question_number)},
            ],
        )
    )


def create_chat_completions_messages(
    subjects: list[str],
    choices: list[str],
    indicate_subject_img_idxes: list[int] | None,
    indicate_choice_imgs: list[str | None] | None,
) -> Iterable[ChatCompletionMessageParam]:
    """
    Azure OpenAIのチャット補完に設定するmessagesを作成する

    Args:
        subjects (list[str]): 問題文/画像URLのリスト
        choices (list[str]): 選択肢のリスト
        indicate_subject_img_idxes (list[int] | None): subjectsで指定した画像URLのインデックスのリスト
        indicate_choice_imgs (list[str | None] | None): choicesの後に続ける画像URLのリスト(画像URLを続けない場合はNone)

    Returns:
        Iterable[ChatCompletionMessageParam]: Azure OpenAIのチャット補完に設定するmessages
    """

    user_content: Iterable[ChatCompletionContentPartParam] = []

    # ユーザープロンプトのヘッダーを生成
    # pylint: disable=line-too-long
    user_content_text: str = """For a given question and the choices, you must generate the correct option/options followed by sentences explaining why each option is correct/incorrect.
Unless there is an instruction such as "Select THREE" in the question, there is basically only one correct option.
For reference, here are two examples.

# First example
Assume that the following question and choices are given:
---
A company is launching a new web service on an Amazon Elastic Container Service (Amazon ECS) cluster. The cluster consists of 100 Amazon EC2 instances. Company policy requires the security group on the cluster instances to block all inbound traffic except HTTPS (port 443).
Which solution will meet these requirements?

0. Change the SSH port to 2222 on the cluster instances by using a user data script. Log in to each instance by using SSH over port 2222.
1. Change the SSH port to 2222 on the cluster instances by using a user data script. Use AWS Trusted Advisor to remotely manage the cluster instances over port 2222.
2. Launch the cluster instances with no SSH key pairs. Use AWS Systems Manager Run Command to remotely manage the cluster instances.
3. Launch the cluster instances with no SSH key pairs. Use AWS Trusted Advisor to remotely manage the cluster instances.
---
For the question and choices in this first example, generate the JSON format with `correct_indexes` and `explanations`.
`correct_indexes` shows an array of indexes of correct options and `explanations` shows an array of explanations of why each option is correct/incorrect.
Since there is no instructions such as "Select THREE" in the question, the number of `correct_indexes` is only one, as follows:
---
{
    "correct_indexes": [2],
    "explanations": [
        "This option is incorrect because the requirements state that the only inbound port that should be open is 443.",
        "This option is incorrect because the requirements state that the only inbound port that should be open is 443.",
        "This option is correct because AWS Systems Manager Run Command requires no inbound ports to be open. Run Command operates entirely over outbound HTTPS, which is open by default for security groups.",
        "This option is incorrect because AWS Trusted Advisor does not perform this management function."
    ]
}
---

# Second Example
Assume that the following question and choices are given:
---
A company has deployed a multi-tier web application in the AWS Cloud. The application consists of the following tiers:
* A Windows-based web tier that is hosted on Amazon EC2 instances with Elastic IP addresses
* A Linux-based application tier that is hosted on EC2 instances that run behind an Application Load Balancer (ALB) that uses path-based routing
* A MySQL database that runs on a Linux EC2 instance
All the EC2 instances are using Intel-based x86 CPUs. A solutions architect needs to modernize the infrastructure to achieve better performance. The solution must minimize the operational overhead of the application.
Which combination of actions should the solutions architect take to meet these requirements? (Select TWO.)

0. Run the MySQL database on multiple EC2 instances.
1. Place the web tier instances behind an ALB.
2. Migrate the MySQL database to Amazon Aurora Serxverless.
3. Migrate all EC2 instance types to Graviton2.
4. Replace the ALB for the application tier instances with a company-managed load balancer.
---
For the question and choices in this second example, generate the JSON format with `correct_indexes` and `explanations`.
`correct_indexes` shows an array of indexes of correct options and `explanations` shows an array of explanations of why each option is correct/incorrect.
Since there is an instruction such as "Select TWO" in the question, the number of `correct_indexes` is two, as follows:
---
{
    "correct_indexes": [1, 2],
    "explanations": [
        "This option is incorrect because additional EC2 instances will not minimize operational overhead. A managed service would be a better option.",
        "This option is correct because you can improve availability and scalability of the web tier by placing the web tier behind an Application Load Balancer (ALB). The ALB serves as the single point of contact for clients and distributes incoming application traffic to the Amazon EC2 instances.",
        "This option is correct because Amazon Aurora Serverless provides high performance and high availability with reduced operational complexity.",
        "This option is incorrect because the application includes Windows instances, which are not available for Graviton2.",
        "This option is incorrect because a company-managed load balancer will not minimize operational overhead."
    ]
}
---

# Main Topic
For the question and choices below, generate the JSON format with `correct_indexes` and `explanations`.
---
"""

    # 各問題文をユーザープロンプトに追記
    for idx, subject in enumerate(subjects):
        if indicate_subject_img_idxes is not None and idx in indicate_subject_img_idxes:
            # 問題文が画像URLの場合は、テキスト(text)と画像URL(image_url)を区別してユーザープロンプトに追記
            user_content.append(
                {
                    "type": "text",
                    "text": user_content_text,
                }
            )
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": subject},
                }
            )
            user_content_text = ""
        else:
            user_content_text += f"{subject}\n"

    if user_content_text != "":
        # 問題文と選択肢との間に改行を追記
        user_content_text += "\n"

    # 各選択肢をユーザープロンプトに追記
    for idx, choice in enumerate(choices):
        user_content_text += f"{idx}. {choice}\n"
        if indicate_choice_imgs is not None and indicate_choice_imgs[idx] is not None:
            # 選択肢の後に画像URLを続ける場合は、テキスト(text)と画像URL(image_url)を区別してユーザープロンプトに追記
            user_content.append(
                {
                    "type": "text",
                    "text": user_content_text,
                }
            )
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": indicate_choice_imgs[idx]},
                }
            )
            user_content_text = ""

    # ユーザープロンプトのフッターを追記
    user_content_text += "---"
    user_content.append(
        {
            "type": "text",
            "text": user_content_text,
        }
    )

    return [
        {
            "role": "developer",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]


def generate_correct_answers(
    subjects: list[str],
    choices: list[str],
    indicate_subject_img_idxes: list[int] | None,
    indicate_choice_imgs: list[str | None] | None,
) -> CorrectAnswers | None:
    """
    正解の選択肢のインデックス・正解/不正解の理由を生成する

    Args:
        subjects (list[str]): 問題文/画像URLのリスト
        choices (list[str]): 選択肢のリスト
        indicate_subject_img_idxes (list[int] | None): subjectsで指定した画像URLのインデックスのリスト
        indicate_choice_imgs (list[str | None] | None): choicesの後に続ける画像URLのリスト(画像URLを続けない場合はNone)

    Returns:
        CorrectAnswers | None: 正解の選択肢のインデックス・正解/不正解の理由(生成できない場合はNone)
    """

    # Azure OpenAIのチャット補完に設定するmessagesを作成
    messages: Iterable[ChatCompletionMessageParam] = create_chat_completions_messages(
        subjects, choices, indicate_subject_img_idxes, indicate_choice_imgs
    )

    try:
        for retry_number in range(MAX_RETRY_NUMBER):
            logging.info({"retry_number": retry_number})

            # AnswerFormatのStructuredOutputでAzure OpenAIのチャット補完を実行
            response = AzureOpenAI(
                api_key=os.environ["OPENAI_API_KEY"],
                api_version=os.environ["OPENAI_API_VERSION"],
                azure_deployment=os.environ["OPENAI_DEPLOYMENT_NAME"],
                azure_endpoint=os.environ["OPENAI_ENDPOINT"],
            ).beta.chat.completions.parse(
                model=os.environ["OPENAI_MODEL_NAME"],
                messages=messages,
                response_format=AnswerFormat,
            )
            logging.info({"parsed": response.choices[0].message.parsed})

            # 正解の選択肢のインデックス・正解/不正解の理由をparseして返す
            # parseできない場合は最大MAX_RETRY_NUMBER回までリトライ可能
            if response.choices[0].message.parsed is not None:
                return CorrectAnswers(
                    correct_indexes=response.choices[0].message.parsed.correct_indexes,
                    explanations=response.choices[0].message.parsed.explanations,
                )
    except Exception as e:
        logging.warning(e)

    return None


def queue_message_answer(message_answer: MessageAnswer) -> None:
    """
    キューストレージにAnswerコンテナーの項目用のメッセージを格納する

    Args:
        message_answer (MessageAnswer): Answerコンテナーの項目用のメッセージ
    """

    connection_string: str = os.environ["AzureWebJobsStorage"]
    if connection_string == "UseDevelopmentStorage=true":
        connection_string = AZURITE_QUEUE_STORAGE_CONNECTION_STRING

    queue_client = QueueClient.from_connection_string(
        conn_str=connection_string,
        queue_name="answers",
        message_encode_policy=BinaryBase64EncodePolicy(),
    )
    logging.info({"message_answer": message_answer})
    queue_client.send_message(json.dumps(message_answer).encode("utf-8"))


bp_post_answer = func.Blueprint()


@bp_post_answer.route(
    route="tests/{testId}/answers/{questionNumber}",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
def post_answer(req: func.HttpRequest) -> func.HttpResponse:
    """
    英語の正解の選択肢・正解/不正解の理由を生成します
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

        # Questionコンテナーの項目を取得し、その項目数をチェック
        items: list[Question] = get_question_items(test_id, question_number)
        logging.info({"items": items})
        if len(items) == 0:
            return func.HttpResponse(body="Not Found Question", status_code=404)
        if len(items) > 1:
            raise ValueError("Not Unique Question")

        # 正解の選択肢・正解/不正解の理由を生成
        correct_answers = generate_correct_answers(
            items[0].get("subjects"),
            items[0].get("choices"),
            items[0].get("indicateSubjectImgIdxes"),
            items[0].get("indicateChoiceImgs"),
        )
        if correct_answers is None:
            raise ValueError("Failed to generate correct answers")

        # キューストレージにメッセージを格納
        queue_message_answer(
            {
                "testId": test_id,
                "questionNumber": question_number,
                "subjects": items[0].get("subjects"),
                "choices": items[0].get("choices"),
                "correctIdxes": correct_answers["correct_indexes"],
                "explanations": correct_answers["explanations"],
                "communityVotes": items[0].get("communityVotes"),
            }
        )

        body: PostAnswerRes = {
            "correctIdxes": correct_answers["correct_indexes"],
            "explanations": correct_answers["explanations"],
            "communityVotes": items[0].get("communityVotes"),
        }
        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
        )
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
