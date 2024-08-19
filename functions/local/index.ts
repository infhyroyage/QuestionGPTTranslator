import { app } from "@azure/functions";
import en2ja from "./en2ja";
import question from "./question";

app.http("en2ja", {
  methods: ["PUT"],
  authLevel: "function",
  handler: en2ja,
});

app.http("question", {
  methods: ["GET"],
  authLevel: "function",
  route: "tests/{testId}/questions/{questionNumber}",
  handler: question,
});
