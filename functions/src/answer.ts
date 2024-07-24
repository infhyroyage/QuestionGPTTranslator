import {
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { PostAnsterReq, PostAnsterRes } from "../functions";

export default async function (
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    const testsStr: string = await request.text();
    const req: PostAnsterReq = testsStr !== "" && JSON.parse(testsStr);
    context.info({ req });

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
