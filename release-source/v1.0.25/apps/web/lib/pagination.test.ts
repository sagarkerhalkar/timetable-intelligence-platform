import { describe, expect, it } from "vitest";
import { clampPage, pageCount, pageNumbers, paginateItems } from "./pagination";

describe("shared page system", () => {
  it("calculates pages and clamps invalid page numbers", () => {
    expect(pageCount(0, 8)).toBe(1);
    expect(pageCount(17, 8)).toBe(3);
    expect(clampPage(99, 17, 8)).toBe(3);
    expect(clampPage(0, 17, 8)).toBe(1);
  });

  it("returns a stable page slice and absolute indexes", () => {
    const result = paginateItems(Array.from({ length: 23 }, (_, index) => index + 1), 2, 10);
    expect(result.items).toEqual([11,12,13,14,15,16,17,18,19,20]);
    expect(result.start).toBe(10);
    expect(result.end).toBe(20);
    expect(result.pages).toBe(3);
  });

  it("creates a compact numeric page window", () => {
    expect(pageNumbers(5, 10, 2)).toEqual([3,4,5,6,7]);
    expect(pageNumbers(1, 2, 2)).toEqual([1,2]);
  });
});
