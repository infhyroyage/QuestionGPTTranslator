import { FeedResponse, ItemResponse, SqlQuerySpec } from "@azure/cosmos";
import {
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { getReadWriteContainer } from "./cosmosDBWrapper";
import { Flag } from "../cosmosDB";
import { translateByAzureTranslator, translateByDeepL } from "./axiosWrapper";
import { PutEn2JaReq, PutEn2JaRes } from "../functions";

const COSMOS_DB_DATABASE_NAME = "Systems";
const COSMOS_DB_CONTAINER_NAME = "Flag";
const COSMOS_DB_ITEMS_ID = "isUsedUpTransLator";

export default async function (
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    const testsStr: string = await request.text();
    const texts: PutEn2JaReq = testsStr !== "" && JSON.parse(testsStr);
    context.info({ texts });

    // Cosmos DBのSystemsデータベースのFlagsコンテナーから、
    // Azure Translatorの無料枠を使い切ったかのフラグを取得
    let isUsedUpTransLator: boolean = false;
    const query: SqlQuerySpec = {
      query: "SELECT * FROM c WHERE c.id = @id",
      parameters: [{ name: "@id", value: COSMOS_DB_ITEMS_ID }],
    };
    const container = getReadWriteContainer(
      COSMOS_DB_DATABASE_NAME,
      COSMOS_DB_CONTAINER_NAME
    );
    const fetchAllResponse: FeedResponse<Flag> = await container.items
      .query<Flag>(query)
      .fetchAll();
    context.info({ fetchAllResponse });

    // 当月中にAzure Translatorの無料枠を使い切ったことがある場合、Azure Translatorにリクエストする必要がないため
    // 最初からDeepLにリクエストを送るように制御する
    if (fetchAllResponse.resources.length > 0) {
      const now: Date = new Date();
      if (
        fetchAllResponse.resources[0].year === now.getFullYear() &&
        fetchAllResponse.resources[0].month === now.getMonth() + 1
      ) {
        isUsedUpTransLator = true;
      } else {
        const deleteResponse: ItemResponse<Flag> = await container
          .item(COSMOS_DB_ITEMS_ID)
          .delete<Flag>();
        context.info({ deleteResponse });
      }
    }

    let jsonBody: PutEn2JaRes | undefined = undefined;
    if (isUsedUpTransLator) {
      jsonBody = await translateByDeepL(texts);
    } else {
      jsonBody = await translateByAzureTranslator(texts);
      if (!jsonBody) {
        // Azure Translatorの無料枠を使い切ったため、Warningログを出力してフラグを設定
        context.warn("Azure Translator Free Tier is used up.");
        const now: Date = new Date();
        const upsertResponse: ItemResponse<Flag> =
          await container.items.upsert<Flag>({
            id: COSMOS_DB_ITEMS_ID,
            year: now.getFullYear(),
            month: now.getMonth() + 1,
          });
        context.info({ upsertResponse });

        jsonBody = await translateByDeepL(texts);
      }
    }
    context.info({ body: jsonBody });
    if (!jsonBody) throw new Error("Translated texts are empty.");

    return { status: 200, jsonBody };
  } catch (e) {
    context.error(e);
    return {
      status: 500,
      body: "Internal Server Error",
    };
  }
}
