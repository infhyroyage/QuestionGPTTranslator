import {
  CosmosClient,
  DatabaseResponse,
  FeedResponse,
  ItemResponse,
  OperationResponse,
  SqlQuerySpec,
  UpsertOperationInput,
} from "@azure/cosmos";
import { Dirent, existsSync, readFileSync, readdirSync } from "fs";
import { join } from "path";
import { v4 as uuidv4 } from "uuid";
import { Question, Test } from "../../types/cosmosDB";
import { ImportData, ImportDatabaseData, ImportItem } from "../../types/import";

/**
 * コマンドライン引数でコース名/テスト名指定した場合は、インポートデータから
 * 指定したコース名/テスト名における項目を抽出して、インポートデータを生成する
 * @returns {ImportData} 抽出した項目のみで構成するインポートデータ
 */
export const createImportData = (): ImportData => {
  // dataファイル/ディレクトリが存在しない場合は空オブジェクトをreturn
  const dataPath = join(process.cwd(), "data");
  if (!existsSync(dataPath)) return {};

  // dataディレクトリに存在する、コース名をすべて取得
  const courseDirectories: string[] = readdirSync(dataPath, {
    withFileTypes: true,
  })
    .filter((dirent: Dirent) => dirent.isDirectory())
    .map((dirent: Dirent) => dirent.name);

  const importData: ImportData = courseDirectories.reduce(
    (result: ImportData, courseName: string) => {
      // コース名のディレクトリに存在する、テスト名をすべて取得
      const testNames: string[] = readdirSync(join(dataPath, courseName))
        .filter((fileName: string) => fileName.endsWith(".json"))
        .map((jsonFileName: string) => jsonFileName.replace(".json", ""));

      const importDatabaseData: ImportDatabaseData = testNames.reduce(
        (dirResult: ImportDatabaseData, testName: string) => {
          // テスト名のjsonファイル名からjsonの中身を読込み
          const importItems: ImportItem[] = JSON.parse(
            readFileSync(join(dataPath, courseName, `${testName}.json`), "utf8")
          );

          dirResult[testName] = importItems;
          return dirResult;
        },
        {}
      );

      result[courseName] = importDatabaseData;
      return result;
    },
    {}
  );

  return importData;
};

/**
 * インポートデータの格納に必要な各データベース、コンテナーをすべて作成する
 * @param {CosmosClient} cosmosClient Cosmos DBのクライアント
 * @returns {Promise<void>}
 */
export const createDatabasesAndContainers = async (
  cosmosClient: CosmosClient
): Promise<void> => {
  let databaseRes: DatabaseResponse;

  // Usersデータベース
  databaseRes = await cosmosClient.databases.createIfNotExists({
    id: "Users",
  });

  // UsersデータベースのTestコンテナー
  await databaseRes.database.containers.createIfNotExists({
    id: "Test",
    partitionKey: "/id",
    // Azure上では複合インデックスを作成するインデックスポリシーを定義しているが、
    // 2023/07/16現在、Azure SDK for JavaScriptでは未サポートのためlocalhost環境上では定義しない
    // https://github.com/Azure/azure-sdk-for-js/issues/21115
    // indexingPolicy: {
    //   compositeIndexes: [
    //     [
    //       {
    //         path: "/courseName",
    //         order: "ascending",
    //       },
    //       {
    //         path: "/testName",
    //         order: "ascending",
    //       },
    //     ],
    //   ],
    // },
  });

  // UsersデータベースのQuestionコンテナー
  await databaseRes.database.containers.createIfNotExists({
    id: "Question",
    partitionKey: "/id",
  });
};

/**
 * インポートデータからUsersテータベースのTestコンテナーの項目を生成する
 * @param {ImportData} importData インポートデータ
 * @param {CosmosClient} cosmosClient Cosmos DBのクライアント
 * @returns {Promise<Test[]>} UsersテータベースのTestコンテナーの項目
 */
export const generateTestItems = async (
  importData: ImportData,
  cosmosClient: CosmosClient
): Promise<Test[]> => {
  // UsersテータベースのTestコンテナーをreadAll
  let insertedTestItems: Test[];
  try {
    const res: FeedResponse<Test> = await cosmosClient
      .database("Users")
      .container("Test")
      .items.readAll<Test>()
      .fetchAll();
    insertedTestItems = res.resources;
  } catch (e) {
    console.log("generateTestItems: Not Found Items");
    insertedTestItems = [];
  }

  return Object.keys(importData).reduce(
    (prevTestItems: Test[], courseName: string) => {
      const innerTestItems: Test[] = Object.keys(importData[courseName]).reduce(
        (prevInnerTestItems: Test[], testName: string) => {
          // UsersテータベースのTestコンテナー格納済の場合は格納した項目、
          // 未格納の場合はundefinedを取得
          const foundTestItem: Test | undefined = insertedTestItems.find(
            (item: Test) =>
              item.courseName === courseName && item.testName === testName
          );

          return [
            ...prevInnerTestItems,
            foundTestItem || {
              courseName,
              testName,
              id: uuidv4(),
              length: importData[courseName][testName].length,
            },
          ];
        },
        []
      );

      return [...prevTestItems, ...innerTestItems];
    },
    []
  );
};

/**
 * UsersテータベースのTestコンテナーの項目をインポートする
 * 項目は比較的要求ユニット(RU)数が少量であるものとする
 * @param {Test[]} testItems UsersテータベースのTestコンテナーの項目
 * @param {CosmosClient} cosmosClient Cosmos DBのクライアント
 * @returns {Promise<void>}
 */
export const importTestItems = async (
  testItems: Test[],
  cosmosClient: CosmosClient
): Promise<void> => {
  // UsersテータベースのTestコンテナーにBulk Upsert
  const bulkResponse: OperationResponse[] = await cosmosClient
    .database("Users")
    .container("Test")
    .items.bulk(
      testItems.map((item: Test): UpsertOperationInput => {
        return {
          operationType: "Upsert",
          partitionKey: item.id,
          resourceBody: item,
        };
      })
    );

  // レスポンス正常性チェック
  const firstErrorRes: OperationResponse | undefined = bulkResponse.find(
    (res: OperationResponse) => res.statusCode >= 400
  );
  if (firstErrorRes) {
    throw new Error(
      `Status Code ${firstErrorRes.statusCode}: ${JSON.stringify(
        firstErrorRes.resourceBody
      )}`
    );
  }
};

/**
 * インポートデータからUsersテータベースのQuestionコンテナーの未格納の項目のみ生成する
 * @param {ImportData} importData インポートデータ
 * @param {CosmosClient} cosmosClient Cosmos DBのクライアント
 * @param {Test[]} testItems UsersテータベースのTestコンテナーの項目
 * @returns {Promise<Question[]>} UsersテータベースQuestionコンテナーの未格納の項目
 */
export const generateQuestionItems = async (
  importData: ImportData,
  cosmosClient: CosmosClient,
  testItems: Test[]
): Promise<Question[]> => {
  // UsersテータベースのQuestionコンテナーの全項目のidをquery
  const query: SqlQuerySpec = {
    query: "SELECT c.id FROM c",
  };
  type QueryResult = { id: string };
  const res: FeedResponse<QueryResult> = await cosmosClient
    .database("Users")
    .container("Question")
    .items.query<QueryResult>(query)
    .fetchAll();
  const insertedQuestionIds: string[] = res.resources.map(
    (resource: QueryResult) => resource.id
  );

  return Object.keys(importData).reduce(
    (prevQuestionItems: Question[], courseName: string) => {
      const innerQuestionItems: Question[] = Object.keys(
        importData[courseName]
      ).reduce((prevInnerQuestionItems: Question[], testName: string) => {
        const testItem: Test | undefined = testItems.find(
          (item: Test) =>
            item.courseName === courseName && item.testName === testName
        );
        if (!testItem) {
          throw new Error(
            `Course Name ${courseName} and Test Name ${testName} Not Found.`
          );
        }

        const testId: string = testItem.id;
        const nonInsertedInnerQuestionItems: Question[] = importData[
          courseName
        ][testName].reduce(
          (prev: Question[], item: ImportItem, idx: number) => {
            if (!insertedQuestionIds.includes(`${testId}_${idx + 1}`)) {
              prev.push({
                ...item,
                id: `${testId}_${idx + 1}`,
                number: idx + 1,
                testId,
              });
            }
            return prev;
          },
          []
        );

        return [...prevInnerQuestionItems, ...nonInsertedInnerQuestionItems];
      }, []);

      return [...prevQuestionItems, ...innerQuestionItems];
    },
    []
  );
};

/**
 * UsersテータベースのQuestionコンテナーの項目をインポートする
 * @link https://docs.microsoft.com/ja-jp/azure/cosmos-db/sql/troubleshoot-request-rate-too-large
 * @param {Question[]} questionItems UsersテータベースのQuestionコンテナーの項目
 * @param {CosmosClient} cosmosClient Cosmos DBのクライアント
 * @returns {Promise<void>}
 */
export const importQuestionItemsAndSleep = async (
  questionItems: Question[],
  cosmosClient: CosmosClient
): Promise<void> => {
  for (let i = 0; i < questionItems.length; i++) {
    const item: Question = questionItems[i];
    const res: ItemResponse<Question> = await cosmosClient
      .database("Users")
      .container("Question")
      .items.upsert<Question>(item);

    // レスポンス正常性チェック
    if (res.statusCode >= 400) {
      throw new Error(`Status Code ${res.statusCode}: ${JSON.stringify(item)}`);
    } else {
      console.log(`${i + 1}th Response OK`);
    }
  }
};
