"""
Module of [POST] /answer
"""

import logging
import os

import azure.functions as func
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_google_community import GoogleSearchAPIWrapper, GoogleSearchRun
from langchain_openai import AzureChatOpenAI

bp_answer = func.Blueprint()


@bp_answer.route(route="answer", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def answer(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate Answers and Explanations from Subjects and Choices
    """

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
    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, handle_parsing_errors=True, verbose=True
    )
    # TODO: Update input
    result = agent_executor.invoke({"input": "What is LangChain?"})
    logging.info(result)

    return func.HttpResponse(result["output"], status_code=200)
