export type Sentence = {
  sentence: string;
  isIndicatedImg: boolean;
  isEscapedTranslation: boolean;
};

export type GetHealthcheck = {
  message: "OK";
};

export type GetQuestion = {
  subjects: Sentence[];
  choices: Sentence[];
  isMultiplied: boolean;
};

export type GetTest = {
  testName: string;
  length: number;
};

export type Test = {
  id: string;
  testName: string;
};
export type GetTests = {
  [course: string]: Test[];
};

export type PutEn2JaReq = string[];
export type PutEn2JaRes = string[];

export type Method = "GET" | "PUT";
