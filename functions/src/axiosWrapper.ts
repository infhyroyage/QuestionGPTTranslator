import axios, { AxiosResponse } from "axios";
import { stringify } from "qs";
import {
  CognitiveResponse,
  CognitiveTranslation,
  DeepLResponse,
  DeepLTranslation,
} from "../translation";

const AZURE_TRANSLATOR_URL: string =
  "https://api.cognitive.microsofttranslator.com/translate";
const DEEPL_URL: string = "https://api-free.deepl.com/v2/translate";

/**
 * 指定した英語の文字列群をAzure Translatorでそれぞれ日本語に翻訳する
 * @param {string[]} texts 英語の文字列群
 * @returns {Promise<string[] | undefined>} 日本語に翻訳した文字列群(Azure Translatorの無料枠を使い切った場合はundefined)
 * @throws Azure Translatorの無料枠を使い切った以外のエラーがスローされた場合
 */
export const translateByAzureTranslator = async (
  texts: string[]
): Promise<string[] | undefined> => {
  if (texts.length === 0) return [];

  const translatorKey: string | undefined = process.env["TRANSLATOR_KEY"];
  if (!translatorKey) {
    throw new Error("Unset TRANSLATOR_KEY");
  }

  try {
    const res: AxiosResponse<CognitiveResponse, any> = await axios.post<
      CognitiveResponse,
      AxiosResponse<CognitiveResponse>,
      { Text: string }[]
    >(
      AZURE_TRANSLATOR_URL,
      texts.map((text: string) => {
        return { Text: text };
      }),
      {
        headers: {
          "Ocp-Apim-Subscription-Key": translatorKey,
          "Ocp-Apim-Subscription-Region": "japaneast",
          "Content-Type": "application/json",
        },
        params: {
          "api-version": "3.0",
          from: "en",
          to: "ja",
        },
        responseType: "json",
      }
    );
    return res.data.map(
      (cognitiveTranslation: CognitiveTranslation) =>
        cognitiveTranslation.translations[0].text
    );
  } catch (error) {
    if (
      axios.isAxiosError(error) &&
      error.response &&
      error.response.status === 403
    ) {
      // Azure Translatorの無料枠を使い切った場合は403エラーとなる
      return undefined;
    } else {
      throw error;
    }
  }
};

/**
 * 指定した英語の文字列群をDeepLでそれぞれ日本語に翻訳する
 * @param {string[]} texts 英語の文字列群
 * @returns {Promise<string[] | undefined>} 日本語に翻訳した文字列群(DeepLの無料枠を使い切った場合はundefined)
 * @throws DeepLの無料枠を使い切った以外のエラーがスローされた場合
 */
export const translateByDeepL = async (
  texts: string[]
): Promise<string[] | undefined> => {
  if (texts.length === 0) return [];

  const auth_key: string | undefined = process.env["DEEPL_AUTH_KEY"];
  if (!auth_key) {
    throw new Error("Unset DEEPL_AUTH_KEY");
  }

  try {
    const res: AxiosResponse<DeepLResponse, any> =
      await axios.get<DeepLResponse>(DEEPL_URL, {
        params: {
          auth_key,
          text: texts,
          source_lang: "EN",
          target_lang: "JA",
          split_sentences: "0",
        },
        paramsSerializer: (params) =>
          stringify(params, { arrayFormat: "repeat" }),
      });
    return res.data.translations.map(
      (deepLTranslation: DeepLTranslation) => deepLTranslation.text
    );
  } catch (error) {
    if (
      axios.isAxiosError(error) &&
      error.response &&
      error.response.status === 456
    ) {
      // DeepLの無料枠を使い切った場合は456エラーとなる
      return undefined;
    } else {
      throw error;
    }
  }
};
