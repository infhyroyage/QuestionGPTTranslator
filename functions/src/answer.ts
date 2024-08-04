import {
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { GoogleCustomSearch } from "@langchain/community/tools/google_custom_search";
import { BaseLanguageModelInterface } from "@langchain/core/language_models/base";
import {
  BasePromptTemplate,
  ChatPromptTemplate,
} from "@langchain/core/prompts";
import { ToolInterface } from "@langchain/core/tools";
import { ChainValues } from "@langchain/core/utils/types";
import { AzureChatOpenAI } from "@langchain/openai";
import { AgentExecutor, createReactAgent } from "langchain/agents";
import { pull } from "langchain/hub";
import { PostAnsterReq, PostAnsterRes } from "../functions";

export default async function (
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    const testsStr: string = await request.text();
    const req: PostAnsterReq = testsStr !== "" && JSON.parse(testsStr);
    context.info({ req });

    const llm: BaseLanguageModelInterface = new AzureChatOpenAI({
      azureOpenAIApiDeploymentName: "gpt-4o",
      azureOpenAIApiKey: process.env["OPENAI_KEY"],
      azureOpenAIApiVersion: "2024-02-15-preview",
      azureOpenAIBasePath:
        "https://westus.api.cognitive.microsoft.com/openai/deployments/",
    });
    const tools: ToolInterface[] = [
      new GoogleCustomSearch({
        apiKey: process.env["GOOGLE_API_KEY"],
        googleCSEId: process.env["GOOGLE_CSE_ID"],
      }),
    ];
    const prompt: BasePromptTemplate = await pull<ChatPromptTemplate>(
      "hwchase17/react"
    );

    const agent = await createReactAgent({ llm, tools, prompt });

    // TODO: Mock
    const executor = new AgentExecutor({
      agent,
      tools,
      verbose: true,
      handleParsingErrors: true,
    });
    const result: ChainValues = await executor.invoke({
      input: "what is LangChain?",
    });
    context.info({ result });

    // TODO: Mock
    let jsonBody: PostAnsterRes = {};
    return { status: 200, jsonBody };
  } catch (e) {
    context.error(e);
    return {
      status: 500,
      body: "Internal Server Error",
    };
  }
}
