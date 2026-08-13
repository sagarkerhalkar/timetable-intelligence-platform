import { describe, expect, it } from "vitest";
import { parseBulkQrRows } from "./qr-bulk";

describe("parseBulkQrRows", () => {
  it("parses Excel or Google Sheets tab-separated rows", () => {
    expect(parseBulkQrRows("Commerce 11th\thttps://example.com/11\nCommerce 12th\thttps://example.com/12")).toEqual([
      { name: "Commerce 11th", url: "https://example.com/11" },
      { name: "Commerce 12th", url: "https://example.com/12" },
    ]);
  });

  it("parses CSV rows", () => {
    expect(parseBulkQrRows('"Science 11th","https://example.com/science-11"')).toEqual([
      { name: "Science 11th", url: "https://example.com/science-11" },
    ]);
  });

  it("parses name followed by a URL", () => {
    expect(parseBulkQrRows("Humanities 12 https://example.com/humanities-12")).toEqual([
      { name: "Humanities 12", url: "https://example.com/humanities-12" },
    ]);
  });

  it("keeps malformed input as a row with an empty URL so the UI can flag it", () => {
    expect(parseBulkQrRows("Missing URL")).toEqual([{ name: "Missing URL", url: "" }]);
  });
});
