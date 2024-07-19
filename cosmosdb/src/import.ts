import { CosmosClient } from "@azure/cosmos";
import { Question, Test } from "../../types/cosmosDB";
import { ImportData } from "../../types/import";
import {
  createDatabasesAndContainers,
  createImportData,
  importTestItems,
  generateTestItems,
  generateQuestionItems,
  importQuestionItemsAndSleep,
} from "./common";

const COSMOSDB_LOCAL_KEY =
  "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==";
const COSMOSDB_LOCAL_URI = "https://localhost:8081";

const main = async () => {
  // インポートデータ作成
  const importData: ImportData = createImportData();
  console.log("createImportData: OK");

  // 各データベース・コンテナー作成
  const cosmosClient: CosmosClient = new CosmosClient({
    endpoint: COSMOSDB_LOCAL_URI,
    key: COSMOSDB_LOCAL_KEY,
  });
  await createDatabasesAndContainers(cosmosClient);
  console.log("createDatabasesAndContainers: OK");

  // UsersテータベースのTestコンテナーの項目を生成
  const testItems: Test[] = await generateTestItems(importData, cosmosClient);
  console.log("generateTestItems: OK");

  // UsersテータベースのTestコンテナーの項目をインポート
  await importTestItems(testItems, cosmosClient);
  console.log("importTestItems: OK");

  // UsersテータベースのQuestionコンテナーの未格納の項目を生成
  const questionItems: Question[] = await generateQuestionItems(
    importData,
    cosmosClient,
    testItems
  );
  console.log("generateQuestionItems: OK");

  // UsersテータベースのQuestionコンテナーの項目をインポート
  await importQuestionItemsAndSleep(questionItems, cosmosClient);
  console.log("importQuestionItemsAndSleep: OK");
};

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
