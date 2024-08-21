"""
Module of [POST] /answer
"""

import json
import logging
import os

import azure.functions as func
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_google_community import GoogleSearchAPIWrapper, GoogleSearchRun
from langchain_openai import AzureChatOpenAI
from type.request import PostAnswerReq

bp_answer = func.Blueprint()


@bp_answer.route(
    route="answer",
    methods=["POST"],
    auth_level=func.AuthLevel.FUNCTION,
)
def answer(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate Answers and Explanations from Subjects and Choices
    """

    try:
        req_body: PostAnswerReq = json.loads(req.get_body().decode("utf-8"))
        course_name: str = req_body["courseName"]
        subjects: list[str] = req_body["subjects"]
        choices: list[str] = req_body["choices"]
        logging.info(
            {"course_name": course_name, "subjects": subjects, "choices": choices}
        )

        # Validate course name, subjects and choices
        if not course_name or course_name == "":
            raise ValueError("Invalid courseName")
        if not subjects or not isinstance(subjects, list) or len(subjects) == 0:
            raise ValueError("Invalid subjects")
        if not choices or not isinstance(choices, list) or len(choices) == 0:
            raise ValueError("Invalid choices")

        # Create ReAct Agent
        llm = AzureChatOpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            api_version=os.environ["OPENAI_API_VERSION"],
            azure_deployment=os.environ["OPENAI_DEPLOYMENT"],
            azure_endpoint=os.environ["OPENAI_ENDPOINT"],
        )
        tools = [
            GoogleSearchRun(
                api_wrapper=GoogleSearchAPIWrapper(
                    google_api_key=os.environ["GOOGLE_API_KEY"],
                    google_cse_id=os.environ["GOOGLE_CSE_ID"],
                )
            )
        ]
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=hub.pull("hwchase17/react"),
        )

        joined_subjects: str = "\n".join(subjects)
        joined_choices: str = "\n".join(
            [f"{idx + 1}. {choice}" for idx, choice in enumerate(choices)]
        )
        # pylint: disable=line-too-long
        prompt: str = f"""You are a professional who provides correct explanations for exam candidates for the exam named "{course_name}".
For a given question and the choices, generate the correct answer options and explanations for why the answers are correct/incorrect.
Unless there is an instruction such as "Select THREE" in the question, there is basically only one correct answer option.
For reference, here are two examples.

# First example
Assume that the following question and choices are given.
---
A company is launching a new web service on an Amazon Elastic Container Service (Amazon ECS) cluster. The cluster consists of 100 Amazon EC2 instances. Company policy requires the security group on the cluster instances to block all inbound traffic except HTTPS (port 443).
Which solution will meet these requirements?

1. Change the SSH port to 2222 on the cluster instances by using a user data script. Log in to each instance by using SSH over port 2222.
2. Change the SSH port to 2222 on the cluster instances by using a user data script. Use AWS Trusted Advisor to remotely manage the cluster instances over port 2222.
3. Launch the cluster instances with no SSH key pairs. Use AWS Systems Manager Run Command to remotely manage the cluster instances.
4. Launch the cluster instances with no SSH key pairs. Use AWS Trusted Advisor to remotely manage the cluster instances.
---
For the question and choices in this first example, generate the following correct answer options and explanations of why the answers are correct/incorrect.
---
The correct answer option is 3.
Option 1 is incorrect because the requirements state that the only inbound port that should be open is 443.
Option 2 is incorrect because the requirements state that the only inbound port that should be open is 443.
Option 3 is correct because AWS Systems Manager Run Command requires no inbound ports to be open. Run Command operates entirely over outbound HTTPS, which is open by default for security groups.
Option 4 is incorrect because AWS Trusted Advisor does not perform this management function.
---

# Second Example
Assume that the following question and choices are given.
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
For the question and choices in this second example, generate the following correct answer options and explanations of why the answers are correct/incorrect.
---
The correct answer option is 2, 3.
Option 1 is incorrect because additional EC2 instances will not minimize operational overhead. A managed service would be a better option.
Option 2 is correct because you can improve availability and scalability of the web tier by placing the web tier behind an Application Load Balancer (ALB). The ALB serves as the single point of contact for clients and distributes incoming application traffic to the Amazon EC2 instances.
Option 3 is correct because Amazon Aurora Serverless provides high performance and high availability with reduced operational complexity.
Option 4 is incorrect because the application includes Windows instances, which are not available for Graviton2.
Option 5 is incorrect because a company-managed load balancer will not minimize operational overhead.
---

# Main Topic
For the question and choices below, generate the correct answer options and explanations for why the answers are correct/incorrect.
Unless there is an instruction such as "Select THREE" in the question, there will generally only be one correct answer choice.
---
{joined_subjects}

{joined_choices}
---"""
        logging.info({"input": prompt})
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            handle_parsing_errors=True,
            verbose=True,
        )
        result = agent_executor.invoke({"input": prompt})
        logging.info({"output": result["output"]})

        return func.HttpResponse(result["output"], status_code=200)
    except Exception as e:  # pylint: disable=broad-except
        logging.error(e)
        return func.HttpResponse(
            body="Internal Server Error",
            status_code=500,
        )
