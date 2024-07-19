export type EscapeTranslatedIdxes = {
  subjects?: number[];
  choices?: number[];
};
export type Question = {
  id: string;
  number: number;
  subjects: string[];
  choices: string[];
  communityVotes: string[];
  indicateSubjectImgIdxes?: number[];
  indicateChoiceImgs?: (string | null)[];
  escapeTranslatedIdxes?: EscapeTranslatedIdxes;
  testId: string;
};

export type Test = {
  id: string;
  courseName: string;
  testName: string;
  length: number;
};

export type Flag = {
  id: string;
  year: number;
  month: number;
};
