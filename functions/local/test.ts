import { FeedResponse, SqlQuerySpec } from "@azure/cosmos";
import {
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { getReadOnlyContainer } from "./cosmosDBWrapper";
import { GetTest } from "../functions";

const COSMOS_DB_DATABASE_NAME = "Users";
const COSMOS_DB_CONTAINER_NAME = "Test";

export default async function (
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    const { testId } = request.params;
    context.info({ testId });

    // Cosmos DBのUsersデータベースのTestコンテナーから項目取得
    const query: SqlQuerySpec = {
      query: "SELECT c.testName, c.length FROM c WHERE c.id = @testId",
      parameters: [{ name: "@testId", value: testId }],
    };
    const response: FeedResponse<GetTest> = await getReadOnlyContainer(
      COSMOS_DB_DATABASE_NAME,
      COSMOS_DB_CONTAINER_NAME
    )
      .items.query<GetTest>(query)
      .fetchAll();
    context.info({ resources: response.resources });

    if (response.resources.length === 0) {
      return {
        status: 404,
        body: "Not Found Test",
      };
    } else if (response.resources.length > 1) {
      throw new Error("Not Unique Test");
    }

    return {
      status: 200,
      body: JSON.stringify(response.resources[0]),
    };
  } catch (e) {
    context.error(e);
    return {
      status: 500,
      body: "Internal Server Error",
    };
  }
}
