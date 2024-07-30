import {
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { AzureChatOpenAI } from "@langchain/openai";
import { PostAnsterReq, PostAnsterRes } from "../functions";

export default async function (
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    const testsStr: string = await request.text();
    const req: PostAnsterReq = testsStr !== "" && JSON.parse(testsStr);
    context.info({ req });

    const model = new AzureChatOpenAI({
      azureOpenAIApiDeploymentName: "gpt-4o",
      azureOpenAIApiKey: process.env["OPENAI_KEY"],
      azureOpenAIApiVersion: "2024-02-15-preview",
      azureOpenAIBasePath:
        "https://westus.api.cognitive.microsoft.com/openai/deployments/",
    });
    const openAIRes = await model.invoke("Hello!");
    context.info({ openAIRes });

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
