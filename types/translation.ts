export type DeepLTranslation = {
  detected_source_language: string;
  text: string;
};
export type DeepLResponse = {
  translations: DeepLTranslation[];
};

export type CognitiveTranslation = {
  translations: {
    text: string;
    to: string;
  }[];
};
export type CognitiveResponse = CognitiveTranslation[];
