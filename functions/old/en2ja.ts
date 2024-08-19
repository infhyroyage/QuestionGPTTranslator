import {
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { PutEn2JaReq, PutEn2JaRes } from "../functions";
import { translateByAzureTranslator, translateByDeepL } from "./axiosWrapper";

export default async function (
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    const testsStr: string = await request.text();
    const texts: PutEn2JaReq = testsStr !== "" && JSON.parse(testsStr);
    context.info({ texts });

    // Azure Translatorで翻訳
    // Azure Translatorの無料枠を使い切った場合はWarningログを出力し、代わりにDeepLで翻訳
    let jsonBody: PutEn2JaRes | undefined = await translateByAzureTranslator(
      texts
    );
    if (!jsonBody) {
      context.warn("Azure Translator Free Tier is used up.");
      jsonBody = await translateByDeepL(texts);
    }
    context.info({ body: jsonBody });
    if (!jsonBody) throw new Error("Cannot translate texts.");

    return { status: 200, jsonBody };
  } catch (e) {
    context.error(e);
    return {
      status: 500,
      body: "Internal Server Error",
    };
  }
}
