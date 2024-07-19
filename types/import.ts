export type ImportItem = {
  /**
   * 問題文または画像URL
   */
  subjects: string[];

  /**
   * 選択肢
   */
  choices: string[];

  /**
   * コミュニティの解答分布(主要な解答のみ)
   */
  communityVotes: string[];

  /**
   * subjectsに存在する画像URLのインデックス群(省略可能)
   */
  indicateSubjectImgIdxes?: number[];

  /**
   * 各選択肢の文末に存在する画像URL(省略可能、nullの場合は画像が存在しない)
   */
  indicateChoiceImgs?: (string | null)[];

  /**
   * 翻訳不必要な文字列のインデックス群(省略可能)
   */
  escapeTranslatedIdxes?: {
    /**
     * subjects(省略可能)
     */
    subjects?: number[];

    /**
     * choices(省略可能)
     */
    choices?: number[];
  };
};
export type ImportDatabaseData = {
  [testName: string]: ImportItem[];
};
export type ImportData = {
  [courseName: string]: ImportDatabaseData;
};
