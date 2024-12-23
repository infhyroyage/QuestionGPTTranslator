"""[POST] /tests/{testId}/answers/{questionNumber} のモジュール"""

import json
import logging
import os

import azure.functions as func
from azure.storage.queue import BinaryBase64EncodePolicy, QueueClient
from openai import AzureOpenAI
from type.message import MessageAnswer
from type.request import PostAnswerReq
from type.response import PostAnswerRes
from type.structured import AnswerFormat
from util.queue import AZURITE_QUEUE_STORAGE_CONNECTION_STRING

MAX_RETRY_NUMBER: int = 5


def create_system_prompt(course_name: str) -> str:
    """
    Azure OpenAIのシステムプロンプトを作成する

    Args:
        course_name (str): コース名

    Returns:
        str: Azure OpenAIのシステムプロンプト
    """

    # pylint: disable=line-too-long
    return f'You are a professional who provides correct explanations for candidates of the exam named "{course_name}".'


def create_user_prompt(subjects: list[str], choices: list[str]) -> str:
    """
    Azure OpenAIのユーザープロンプトを作成する

    Args:
        subjects (list[str]): 問題文
        choices (list[str]): 選択肢

    Returns:
        str: Azure OpenAIのユーザープロンプト
    """

    joined_subjects: str = "\n".join(subjects)
    joined_choices: str = "\n".join(
        [f"{idx + 1}. {choice}" for idx, choice in enumerate(choices)]
    )

    # pylint: disable=line-too-long
    return f"""For a given question and the choices, you must generate sentences that show the correct option/options and explain why each option is correct/incorrect.
Unless there is an instruction such as "Select THREE" in the question, there is basically only one correct option.
For reference, here are two examples.

# First example
Assume that the following question and choices are given:
---
A company is launching a new web service on an Amazon Elastic Container Service (Amazon ECS) cluster. The cluster consists of 100 Amazon EC2 instances. Company policy requires the security group on the cluster instances to block all inbound traffic except HTTPS (port 443).
Which solution will meet these requirements?

1. Change the SSH port to 2222 on the cluster instances by using a user data script. Log in to each instance by using SSH over port 2222.
2. Change the SSH port to 2222 on the cluster instances by using a user data script. Use AWS Trusted Advisor to remotely manage the cluster instances over port 2222.
3. Launch the cluster instances with no SSH key pairs. Use AWS Systems Manager Run Command to remotely manage the cluster instances.
4. Launch the cluster instances with no SSH key pairs. Use AWS Trusted Advisor to remotely manage the cluster instances.
---
For the question and choices in this first example, generate a sentence that shows the correct option, starting with "Correct Option: ", followed by sentences that explain why each option is correct/incorrect, as follows:
---
Correct Option: 3
Option 1 is incorrect because the requirements state that the only inbound port that should be open is 443.
Option 2 is incorrect because the requirements state that the only inbound port that should be open is 443.
Option 3 is correct because AWS Systems Manager Run Command requires no inbound ports to be open. Run Command operates entirely over outbound HTTPS, which is open by default for security groups.
Option 4 is incorrect because AWS Trusted Advisor does not perform this management function.
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

1. Run the MySQL database on multiple EC2 instances.
2. Place the web tier instances behind an ALB.
3. Migrate the MySQL database to Amazon Aurora Serxverless.
4. Migrate all EC2 instance types to Graviton2.
5. Replace the ALB for the application tier instances with a company-managed load balancer.
---
For the question and choices in this second example, generate a sentence that shows the correct options, starting with "Correct Options: ", followed by sentences that explain why each option is correct/incorrect, as follows:
---
Correct Options: 2, 3
Option 1 is incorrect because additional EC2 instances will not minimize operational overhead. A managed service would be a better option.
Option 2 is correct because you can improve availability and scalability of the web tier by placing the web tier behind an Application Load Balancer (ALB). The ALB serves as the single point of contact for clients and distributes incoming application traffic to the Amazon EC2 instances.
Option 3 is correct because Amazon Aurora Serverless provides high performance and high availability with reduced operational complexity.
Option 4 is incorrect because the application includes Windows instances, which are not available for Graviton2.
Option 5 is incorrect because a company-managed load balancer will not minimize operational overhead.
---

# Main Topic
For the question and choices below, generate sentences that show the correct option/options and explain why each option is correct/incorrect.
Unless there is an instruction such as "Select THREE" in the question, there will generally only be one correct option.
---
{joined_subjects}

{joined_choices}
---"""


def generate_correct_answers(
    course_name: str, subjects: list[str], choices: list[str]
) -> tuple[list[int] | None, list[str] | None]:
    """
    正解の選択肢・正解/不正解の理由を生成する

    Args:
        course_name (str): コース名
        subjects (list[str]): 問題文のリスト
        choices (list[str]): 選択肢のリスト

    Returns:
        tuple[list[int] | None, list[str] | None]: 正解のインデックスと説明のリスト
    """
    correct_indexes: list[int] | None = None
    explanations: list[str] | None = None
    for retry_number in range(MAX_RETRY_NUMBER):
        logging.info({"retry_number": retry_number})
        try:
            response = AzureOpenAI(
                api_key=os.environ["OPENAI_API_KEY"],
                api_version=os.environ["OPENAI_API_VERSION"],
                azure_deployment=os.environ["OPENAI_DEPLOYMENT"],
                azure_endpoint=os.environ["OPENAI_ENDPOINT"],
            ).beta.chat.completions.parse(
                model=os.environ["OPENAI_MODEL"],
                messages=[
                    {
                        "role": "system",
                        "content": create_system_prompt(course_name),
                    },
                    {
                        "role": "user",
                        "content": create_user_prompt(subjects, choices),
                    },
                ],
                response_format=AnswerFormat,
            )
            logging.info({"message": response.choices[0].message})

            # parseできるかのチェック
            if response.choices[0].message.parsed is not None:
                correct_indexes = response.choices[0].message.parsed.correct_indexes
                explanations = response.choices[0].message.parsed.explanations
                break
        except Exception as e:
            logging.warning(e)
    return correct_indexes, explanations


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
    英語の問題文・選択肢の文章から、英語の正解の選択肢・正解/不正解の理由を生成します
    """

    try:
        test_id = req.route_params.get("testId")
        question_number = req.route_params.get("questionNumber")
        req_body: PostAnswerReq = json.loads(req.get_body().decode("utf-8"))
        course_name: str = req_body["courseName"]
        subjects: list[str] = req_body["subjects"]
        choices: list[str] = req_body["choices"]
        logging.info(
            {
                "course_name": course_name,
                "question_number": question_number,
                "test_id": test_id,
                "subjects": subjects,
                "choices": choices,
            }
        )

        # パスパラメーター・リクエストボディのバリデーションチェック
        if test_id is None or question_number is None:
            raise ValueError(
                f"Invalid testId or questionNumber: {test_id}, {question_number}"
            )
        if not question_number.isdigit():
            return func.HttpResponse(
                body=f"Invalid questionNumber: {question_number}", status_code=400
            )
        if not course_name or course_name == "":
            raise ValueError("Invalid courseName")
        if not subjects or not isinstance(subjects, list) or len(subjects) == 0:
            raise ValueError("Invalid subjects")
        if not choices or not isinstance(choices, list) or len(choices) == 0:
            raise ValueError("Invalid choices")

        # 正解の選択肢・正解/不正解の理由をAzure OpenAIのStructured Outputsでparseして生成
        correct_indexes, explanations = generate_correct_answers(
            course_name, subjects, choices
        )

        # リトライ回数超過チェック
        if not correct_indexes or not explanations:
            raise RuntimeError("Too Many Retries")

        # キューストレージにメッセージを格納
        queue_message_answer(
            {
                "testId": test_id,
                "questionNumber": question_number,
                "subjects": subjects,
                "choices": choices,
                "correctIndexes": correct_indexes,
                "explanations": explanations,
            }
        )

        body: PostAnswerRes = {
            "correctIdxes": correct_indexes,
            "explanations": explanations,
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
