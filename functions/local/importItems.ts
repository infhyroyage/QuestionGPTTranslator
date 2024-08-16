import { FeedResponse, ItemResponse, SqlQuerySpec } from "@azure/cosmos";
import { FunctionResult, InvocationContext } from "@azure/functions";
import deepEqual from "fast-deep-equal";
import { v4 as uuidv4 } from "uuid";
import { EscapeTranslatedIdxes, Question, Test } from "../cosmosDB";
import { ImportItem } from "../import";
import { getReadOnlyContainer, getReadWriteContainer } from "./cosmosDBWrapper";

const COSMOS_DB_DATABASE_NAME = "Users";
const COSMOS_DB_CONTAINER_NAMES = { test: "Test", question: "Question" };

export default async function (
  blob: unknown,
  context: InvocationContext
): Promise<FunctionResult> {
  try {
    // Blobトリガーで受け取ったメタデータから可変パラメーターを取得
    const metadata = context.triggerMetadata as Record<string, string>;
    const courseName: string = metadata.courseName as string;
    const testName: string = metadata.testName as string;
    context.info({ courseName, testName });

    // Blobトリガーで受け取ったjsonファイルのバイナリデータをImportItem[]型として読込み
    const jsonData: ImportItem[] = JSON.parse((blob as Buffer).toString());

    // UsersテータベースのTestコンテナーの項目を取得
    const testQuery: SqlQuerySpec = {
      query:
        "SELECT * FROM c WHERE c.courseName = @courseName and c.testName = @testName",
      parameters: [
        { name: "@courseName", value: courseName },
        { name: "@testName", value: testName },
      ],
    };
    const insertedTestItemsRes: FeedResponse<Test> = await getReadOnlyContainer(
      COSMOS_DB_DATABASE_NAME,
      COSMOS_DB_CONTAINER_NAMES.test
    )
      .items.query<Test>(testQuery)
      .fetchAll();
    const insertedTestItems: Test[] = insertedTestItemsRes.resources;
    context.info({ insertedTestItems });
    if (insertedTestItems.length > 1) {
      throw new Error("Not Unique Test");
    }

    // 取得したUsersテータベースのTestコンテナーの項目が存在し差分がない場合以外はupsert
    let testId: string;
    if (
      insertedTestItems.length === 0 ||
      (insertedTestItems.length === 1 &&
        insertedTestItems[0].length !== jsonData.length)
    ) {
      testId =
        insertedTestItems.length === 0 ? uuidv4() : insertedTestItems[0].id;
      const upsertTestItem: Test = {
        courseName,
        testName,
        id: testId,
        length: jsonData.length,
      };
      context.info({ upsertTestItem });
      const res: ItemResponse<Test> = await getReadWriteContainer(
        COSMOS_DB_DATABASE_NAME,
        COSMOS_DB_CONTAINER_NAMES.test
      ).items.upsert<Test>(upsertTestItem);
      if (res.statusCode >= 400) {
        throw new Error(
          `Status Code ${res.statusCode}: ${JSON.stringify(upsertTestItem)}`
        );
      }
    } else {
      testId = insertedTestItems[0].id;
    }

    // UsersテータベースのQuestionコンテナーの項目を全取得
    let insertedQuestionItems: Question[] = [];
    if (insertedTestItems.length > 0) {
      // UsersテータベースのTestコンテナーの項目が取得できた場合のみクエリを実行
      const questionQuery: SqlQuerySpec = {
        query: "SELECT * FROM c WHERE c.testId = @testId",
        parameters: [{ name: "@testId", value: testId }],
      };
      const insertedQuestionItemsRes: FeedResponse<Question> =
        await getReadOnlyContainer(
          COSMOS_DB_DATABASE_NAME,
          COSMOS_DB_CONTAINER_NAMES.question
        )
          .items.query<Question>(questionQuery)
          .fetchAll();
      insertedQuestionItems = insertedQuestionItemsRes.resources;
    }

    // 読み込んだjsonファイルの各ImportItemにて、取得したUsersテータベースの
    // Questionコンテナーに存在して差分がない項目を抽出
    const insertedImportItems: ImportItem[] = insertedQuestionItems.map(
      (insertedQuestionItem: Question) => {
        const insertedImportItem: ImportItem = {
          subjects: insertedQuestionItem.subjects,
          choices: insertedQuestionItem.choices,
          communityVotes: insertedQuestionItem.communityVotes,
        };
        if (insertedQuestionItem.indicateSubjectImgIdxes) {
          insertedImportItem.indicateSubjectImgIdxes =
            insertedQuestionItem.indicateSubjectImgIdxes;
        }
        if (insertedQuestionItem.indicateChoiceImgs) {
          insertedImportItem.indicateChoiceImgs =
            insertedQuestionItem.indicateChoiceImgs;
        }
        if (insertedQuestionItem.escapeTranslatedIdxes) {
          const escapeTranslatedIdxes: EscapeTranslatedIdxes = {};
          if (insertedQuestionItem.escapeTranslatedIdxes.subjects) {
            escapeTranslatedIdxes.subjects =
              insertedQuestionItem.escapeTranslatedIdxes.subjects;
          }
          if (insertedQuestionItem.escapeTranslatedIdxes.choices) {
            escapeTranslatedIdxes.choices =
              insertedQuestionItem.escapeTranslatedIdxes.choices;
          }
          insertedImportItem.escapeTranslatedIdxes = escapeTranslatedIdxes;
        }
        return insertedImportItem;
      }
    );
    context.info({ insertedImportItems });
    const upsertImportItems: ImportItem[] = jsonData.reduce(
      (prev: ImportItem[], jsonImportItem: ImportItem) => {
        const insertedQuestionItem: ImportItem | undefined =
          insertedImportItems.find((insertedImportItem: ImportItem) =>
            deepEqual(insertedImportItem, jsonImportItem)
          );
        if (!insertedQuestionItem) {
          prev.push(jsonImportItem);
        }
        return prev;
      },
      []
    );
    context.info({ upsertImportItems });

    // 暗号化したUsersテータベースのQuestionコンテナーの各項目をupsert
    // 比較的要求ユニット(RU)数が多いDB操作を行うため、upsertの合間に3秒間sleepする
    // https://docs.microsoft.com/ja-jp/azure/cosmos-db/sql/troubleshoot-request-rate-too-large
    if (upsertImportItems.length > 0) {
      const sleep = (sleepPeriod: number): Promise<unknown> =>
        new Promise((resolve) => setTimeout(resolve, sleepPeriod));

      for (let idx = 0; idx < upsertImportItems.length; idx++) {
        const item: Question = {
          ...upsertImportItems[idx],
          id: `${testId}_${idx + 1}`,
          number: idx + 1,
          testId,
        };
        const res: ItemResponse<Question> = await getReadWriteContainer(
          COSMOS_DB_DATABASE_NAME,
          COSMOS_DB_CONTAINER_NAMES.question
        ).items.upsert<Question>(item);
        if (res.statusCode >= 400) {
          throw new Error(
            `Status Code ${res.statusCode}: ${JSON.stringify(item)}`
          );
        }

        await sleep(3000);
      }
    }

    return {
      status: 200,
      body: "OK",
    };
  } catch (e) {
    context.error(e);
    return {
      status: 500,
      body: "Internal Server Error",
    };
  }
}
