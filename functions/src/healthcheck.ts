import { HttpResponseInit } from "@azure/functions";

export default async function (): Promise<HttpResponseInit> {
  return {
    status: 200,
    body: "OK",
  };
}
