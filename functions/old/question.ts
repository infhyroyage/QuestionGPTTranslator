import { FeedResponse, SqlQuerySpec } from "@azure/cosmos";
import {
  HttpRequest,
  HttpResponseInit,
  InvocationContext,
} from "@azure/functions";
import { Question } from "../cosmosDB";
import { GetQuestion } from "../functions";
import { getReadOnlyContainer } from "./cosmosDBWrapper";

const COSMOS_DB_DATABASE_NAME = "Users";
const COSMOS_DB_CONTAINER_NAME = "Question";

export default async function (
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    const { testId, questionNumber } = request.params;
    context.info({ testId, questionNumber });

    // questionNumberのバリデーションチェック
    if (isNaN(parseInt(questionNumber))) {
      return {
        status: 400,
        body: `Invalid questionNumber: ${questionNumber}`,
      };
    }

    // Cosmos DBのUsersデータベースのQuestionコンテナーから項目取得
    type QueryQuestion = Pick<
      Question,
      | "subjects"
      | "choices"
      | "communityVotes"
      | "indicateSubjectImgIdxes"
      | "indicateChoiceImgs"
      | "escapeTranslatedIdxes"
    >;
    const query: SqlQuerySpec = {
      query:
        "SELECT c.subjects, c.choices, c.communityVotes, c.indicateSubjectImgIdxes, c.indicateChoiceImgs, c.escapeTranslatedIdxes FROM c WHERE c.testId = @testId AND c.number = @number",
      parameters: [
        { name: "@testId", value: testId },
        { name: "@number", value: parseInt(questionNumber) },
      ],
    };
    const response: FeedResponse<QueryQuestion> = await getReadOnlyContainer(
      COSMOS_DB_DATABASE_NAME,
      COSMOS_DB_CONTAINER_NAME
    )
      .items.query<QueryQuestion>(query)
      .fetchAll();
    context.info({ resources: response.resources });

    if (response.resources.length === 0) {
      return {
        status: 404,
        body: "Not Found Question",
      };
    } else if (response.resources.length > 1) {
      throw new Error("Not Unique Question");
    }
    const result: QueryQuestion = response.resources[0];

    // communityVotesの最初の要素が「AB (100%)」のような形式の場合は回答が複数個、
    // 「A (100%)」のような形式の場合は回答が1個のみ存在すると判定
    const isMultiplied: boolean =
      result.communityVotes[0].match(/^[A-Z]{2,} \(\d+%\)$/) !== null;

    const body: GetQuestion = {
      subjects: result.subjects.map((subject: string, idx: number) => {
        return {
          sentence: subject,
          isIndicatedImg:
            !!result.indicateSubjectImgIdxes &&
            result.indicateSubjectImgIdxes.includes(idx),
          isEscapedTranslation:
            !!result.escapeTranslatedIdxes &&
            !!result.escapeTranslatedIdxes.subjects &&
            result.escapeTranslatedIdxes.subjects.includes(idx),
        };
      }),
      choices: result.choices.map((choice: string, idx: number) => {
        const imgTmp: string | null | undefined =
          result.indicateChoiceImgs && result.indicateChoiceImgs[idx];
        return {
          sentence: choice,
          img: imgTmp !== null ? imgTmp : undefined,
          isEscapedTranslation:
            !!result.escapeTranslatedIdxes &&
            !!result.escapeTranslatedIdxes.choices &&
            result.escapeTranslatedIdxes.choices.includes(idx),
        };
      }),
      isMultiplied,
    };
    context.info({ body });

    return {
      status: 200,
      body: JSON.stringify(body),
    };
  } catch (e) {
    context.error(e);
    return {
      status: 500,
      body: "Internal Server Error",
    };
  }
}
