"""
Module of [POST] /tests/{testId}/answers/{questionNumber}
"""

import json
import logging
import os
import re
from typing import Sequence

import azure.functions as func
from azure.storage.queue import BinaryBase64EncodePolicy, QueueClient
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_google_community import GoogleSearchAPIWrapper, GoogleSearchRun
from langchain_openai import AzureChatOpenAI
from type.message import MessageAnswer
from type.request import PostAnswerReq
from type.response import PostAnswerRes

MAX_RETRY_NUMBER: int = 5

bp_answer = func.Blueprint()


def create_input(course_name: str, subjects: list[str], choices: list[str]) -> str:
    """
    Create Input Prompt
    """

    joined_subjects: str = "\n".join(subjects)
    joined_choices: str = "\n".join(
        [f"{idx + 1}. {choice}" for idx, choice in enumerate(choices)]
    )

    # pylint: disable=line-too-long
    return f"""You are a professional who provides correct explanations for candidates of the exam named "{course_name}".
For a given question and the choices, you must generate sentences that show the correct option/options and explain why each option is correct/incorrect.
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


def generate_correct_indexes_explanations(
    agent: Runnable,
    tools: Sequence[BaseTool],
    course_name: str,
    subjects: list[str],
    choices: list[str],
) -> tuple[list[int] | None, list[str] | None]:
    """
    Generate correct indexes and explanations from Subjects and Choices
    If failed, return (None, None).
    """

    correct_indexes: list[int] | None = None
    explanations: list[str] | None = None
    try:
        # Execute ReAct agent
        output: str = AgentExecutor(
            agent=agent,
            tools=tools,
            handle_parsing_errors=True,
            verbose=True,
        ).invoke({"input": create_input(course_name, subjects, choices)})["output"]
        logging.info({"output": output})

        # Check if output format is "Correct Option: {raw_correct_options}\n{raw_explanations}"
        # or "Correct Options: {raw_correct_options}\n{raw_explanations}"
        match = re.search(r"Correct Option[s]?: (\d+(?:, \d+)*)\n([\s\S]+)", output)
        if match and match.group(1) and match.group(2):
            raw_correct_options: str = match.group(1)
            raw_explanations: str = match.group(2)
            logging.info(
                {
                    "raw_correct_options": raw_correct_options,
                    "raw_explanations": raw_explanations,
                }
            )

            # Clean up correct options and explanations
            correct_indexes = [
                int(option.strip()) - 1
                for option in raw_correct_options.split(", ")
                if option.strip()
            ]
            explanations = [
                exp.strip() for exp in raw_explanations.split("\n") if exp.strip()
            ]
    except Exception as e:  # pylint: disable=broad-except
        logging.warning(e)

    return correct_indexes, explanations


def queue_message_answer(
    test_id: str,
    question_number: int,
    subjects: list[str],
    choices: list[str],
    correct_indexes: list[int],
    explanations: list[str],
) -> None:
    """
    Queue Message for Answer Item to Queue Storage
    """

    queue_client = QueueClient.from_connection_string(
        conn_str=os.environ["AzureWebJobsStorage"],
        queue_name="answers",
        message_encode_policy=BinaryBase64EncodePolicy(),
    )
    message_answer: MessageAnswer = {
        "testId": test_id,
        "questionNumber": question_number,
        "subjects": subjects,
        "choices": choices,
        "correctIndexes": correct_indexes,
        "explanations": explanations,
    }
    logging.info({"message_answer": message_answer})
    queue_client.send_message(json.dumps(message_answer).encode("utf-8"))


@bp_answer.route(
    route="tests/{testId}/answers/{questionNumber}",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
def answer(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate Answers and Explanations
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

        # Validate Path Parameters and Body
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

        # Create ReAct agent
        llm = AzureChatOpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            api_version=os.environ["OPENAI_API_VERSION"],
            azure_deployment=os.environ["OPENAI_DEPLOYMENT"],
            azure_endpoint=os.environ["OPENAI_ENDPOINT"],
        )
        tools: Sequence[BaseTool] = [
            GoogleSearchRun(
                api_wrapper=GoogleSearchAPIWrapper(
                    google_api_key=os.environ["GOOGLE_API_KEY"],
                    google_cse_id=os.environ["GOOGLE_CSE_ID"],
                )
            )
        ]
        agent: Runnable = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=hub.pull("hwchase17/react"),
        )

        # Generate correct indexes and explanations within MAX_RETRY_NUMBER retries
        correct_indexes: list[int] | None = None
        explanations: list[str] | None = None
        for retry_number in range(MAX_RETRY_NUMBER):
            logging.info({"retry_number": retry_number})
            correct_indexes, explanations = generate_correct_indexes_explanations(
                agent=agent,
                tools=tools,
                course_name=course_name,
                subjects=subjects,
                choices=choices,
            )

            # Check if correct indexes and explanations are valid
            if correct_indexes and explanations:
                break

        # Check if max retries reached
        if not correct_indexes or not explanations:
            raise RuntimeError("Too Many Retries")

        # Queue answer to queue storage
        queue_message_answer(
            test_id=test_id,
            question_number=question_number,
            subjects=subjects,
            choices=choices,
            correct_indexes=correct_indexes,
            explanations=explanations,
        )

        body: PostAnswerRes = {
            "correctIdxes": correct_indexes,
            "explanations": explanations,
        }
        return func.HttpResponse(
            body=json.dumps(body),
            status_code=200,
        )
    except Exception as e:  # pylint: disable=broad-except
        logging.error(e)
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
