export type GetHealthcheck = {
  message: "OK";
};

export type Subject = {
  sentence: string;
  isIndicatedImg: boolean;
  isEscapedTranslation: boolean;
};
export type Choice = {
  sentence: string;
  img?: string;
  isEscapedTranslation: boolean;
};
export type GetQuestion = {
  subjects: Subject[];
  choices: Choice[];
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

export type PostAnsterReq = {
  subjects: string[];
  choices: string[];
};
export type PostAnsterRes = {
  correctIdxes?: number[];
  explanations?: string[];
};

export type PutEn2JaReq = string[];
export type PutEn2JaRes = string[];

export type Method = "GET" | "POST" | "PUT";
