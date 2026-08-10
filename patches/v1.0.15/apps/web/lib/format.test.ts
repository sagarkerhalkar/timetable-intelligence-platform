import { describe, expect, it } from "vitest";
import {
  confidenceLabel,
  formatDateTime,
  formatNumber,
  formatTime,
  indiaWeekDates
} from "./format";

describe("format helpers", () => {
  it("formats Indian number grouping", () => {
    expect(formatNumber(1234567)).toBe("12,34,567");
  });

  it("formats 24-hour API time", () => {
    expect(formatTime("18:30:00")).toBe("6:30 PM");
    expect(formatTime(null)).toBe("Time pending");
  });

  it("labels parser confidence", () => {
    expect(confidenceLabel(0.9)).toBe("High");
    expect(confidenceLabel(0.6)).toBe("Review");
    expect(confidenceLabel(0.2)).toBe("Low");
  });

  it("handles missing and invalid dates", () => {
    expect(formatDateTime(null)).toBe("Not checked yet");
    expect(formatDateTime("bad")).toBe("Date unavailable");
  });

  it("keeps Monday in the current India week", () => {
    expect(indiaWeekDates("2026-08-10")).toEqual([
      "2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13",
      "2026-08-14", "2026-08-15", "2026-08-16"
    ]);
  });

  it("maps Sunday to the Monday of the same India week", () => {
    expect(indiaWeekDates("2026-08-16")).toEqual([
      "2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13",
      "2026-08-14", "2026-08-15", "2026-08-16"
    ]);
  });

  it("handles month and year week boundaries without timezone drift", () => {
    expect(indiaWeekDates("2027-01-01")).toEqual([
      "2026-12-28", "2026-12-29", "2026-12-30", "2026-12-31",
      "2027-01-01", "2027-01-02", "2027-01-03"
    ]);
  });

  it("rejects invalid civil week anchors", () => {
    expect(indiaWeekDates("2026-02-31")).toEqual([]);
    expect(indiaWeekDates("bad")).toEqual([]);
  });
});
