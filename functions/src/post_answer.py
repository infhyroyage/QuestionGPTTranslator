"""[POST] /tests/{testId}/answers/{questionNumber} のモジュール"""

import json
import logging
import os

import azure.functions as func
from azure.storage.queue import BinaryBase64EncodePolicy, QueueClient
from openai import AzureOpenAI
from type.message import MessageAnswer
from type.openai import CorrectAnswers
from type.request import PostAnswerReq
from type.response import PostAnswerRes
from type.structured import AnswerFormat
from util.queue import AZURITE_QUEUE_STORAGE_CONNECTION_STRING

MAX_RETRY_NUMBER: int = 5


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

    req_body_encoded: bytes = req.get_body()
    if not req_body_encoded:
        errors.append("Request Body is Empty")
    else:
        req_body: PostAnswerReq = json.loads(req_body_encoded.decode("utf-8"))

        course_name = req_body.get("courseName")
        if not course_name or course_name == "":
            errors.append("courseName is Empty")

        subjects = req_body.get("subjects")
        if not subjects:
            errors.append("subjects is Empty")
        elif not isinstance(subjects, list):
            errors.append(f"Invalid subjects: {subjects}")

        choices = req_body.get("choices")
        if not choices:
            errors.append("choices is Empty")
        elif not isinstance(choices, list):
            errors.append(f"Invalid choices: {choices}")

    return errors[0] if errors else None


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
) -> CorrectAnswers | None:
    """
    Azure OpenAIにコールして、正解の選択肢のインデックス・正解/不正解の理由を生成する

    Args:
        course_name (str): コース名
        subjects (list[str]): 問題文のリスト
        choices (list[str]): 選択肢のリスト

    Returns:
        CorrectAnswers | None: 正解の選択肢のインデックス・正解/不正解の理由(生成できない場合はNone)
    """

    system_prompt: str = create_system_prompt(course_name)
    user_prompt: str = create_user_prompt(subjects, choices)

    try:
        for retry_number in range(MAX_RETRY_NUMBER):
            logging.info({"retry_number": retry_number})

            # Azure OpenAIのレスポンスを取得
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
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
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
    英語の問題文・選択肢の文章から、英語の正解の選択肢・正解/不正解の理由を生成します
    """

    try:
        # バリデーションチェック
        error_message = validate_request(req)
        if error_message:
            return func.HttpResponse(body=error_message, status_code=400)

        req_body: PostAnswerReq = json.loads(req.get_body().decode("utf-8"))
        course_name = req_body.get("courseName")
        subjects = req_body.get("subjects")
        choices = req_body.get("choices")
        test_id = req.route_params.get("testId")
        question_number = req.route_params.get("questionNumber")

        logging.info(
            {
                "course_name": course_name,
                "question_number": question_number,
                "test_id": test_id,
                "subjects": subjects,
                "choices": choices,
            }
        )

        # 正解の選択肢・正解/不正解の理由を生成
        correct_answers = generate_correct_answers(course_name, subjects, choices)
        if correct_answers is None:
            raise ValueError("Failed to generate correct answers")

        # キューストレージにメッセージを格納
        queue_message_answer(
            {
                "testId": test_id,
                "questionNumber": question_number,
                "subjects": subjects,
                "choices": choices,
                "correctIdxes": correct_answers["correct_indexes"],
                "explanations": correct_answers["explanations"],
            }
        )

        body: PostAnswerRes = {
            "correctIdxes": correct_answers["correct_indexes"],
            "explanations": correct_answers["explanations"],
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
