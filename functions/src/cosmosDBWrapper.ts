import { CosmosClient, Container } from "@azure/cosmos";

/**
 * 指定したCosmos DBアカウントのコンテナーの読み取り専用インスタンスを返す
 * @param {string} databaseName Cosmos DBアカウントのデータベース名
 * @param {string} containerName Cosmos DBアカウントのコンテナー名
 * @returns {Container} Cosmos DBアカウントのコンテナーの読み取り専用インスタンス
 */
export const getReadOnlyContainer = (
  databaseName: string,
  containerName: string
): Container => {
  const endpoint: string | undefined = process.env["COSMOSDB_URI"];
  if (!endpoint) {
    throw new Error("Unset COSMOSDB_URI");
  }

  const key: string | undefined = process.env["COSMOSDB_READONLY_KEY"];
  if (!key) {
    throw new Error("Unset COSMOSDB_READONLY_KEY");
  }

  return new CosmosClient({ endpoint, key })
    .database(databaseName)
    .container(containerName);
};

/**
 * 指定したCosmos DBアカウントのコンテナーのインスタンスを返す
 * @param {string} databaseName Cosmos DBアカウントのデータベース名
 * @param {string} containerName Cosmos DBアカウントのコンテナー名
 * @returns {Container} Cosmos DBアカウントのコンテナーのインスタンス
 */
export const getReadWriteContainer = (
  databaseName: string,
  containerName: string
): Container => {
  const endpoint: string | undefined = process.env["COSMOSDB_URI"];
  if (!endpoint) {
    throw new Error("Unset COSMOSDB_URI");
  }

  const key: string | undefined = process.env["COSMOSDB_KEY"];
  if (!key) {
    throw new Error("Unset COSMOSDB_KEY");
  }

  return new CosmosClient({ endpoint, key })
    .database(databaseName)
    .container(containerName);
};
