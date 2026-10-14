import { describe, expect, it } from "vitest";
import { resolveActiveNavigationHref } from "./navigation";

describe("exact navigation selection", () => {
  it("selects only the most specific QR route", () => {
    expect(resolveActiveNavigationHref("/qr")).toBe("/qr");
    expect(resolveActiveNavigationHref("/qr/templates")).toBe("/qr/templates");
    expect(resolveActiveNavigationHref("/qr/bulk")).toBe("/qr/bulk");
    expect(resolveActiveNavigationHref("/qr/codes")).toBe("/qr/codes");
    expect(resolveActiveNavigationHref("/qr/stats")).toBe("/qr/stats");
    expect(resolveActiveNavigationHref("/qr/codes/details")).toBe("/qr/codes");
  });

  it("does not let the parent QR route remain selected on child pages", () => {
    const hrefs = ["/qr", "/qr/templates", "/qr/bulk", "/qr/codes", "/qr/stats"] as const;
    expect(resolveActiveNavigationHref("/qr/templates", hrefs)).not.toBe("/qr");
    expect(resolveActiveNavigationHref("/qr/bulk", hrefs)).not.toBe("/qr");
    expect(resolveActiveNavigationHref("/qr/codes", hrefs)).not.toBe("/qr");
    expect(resolveActiveNavigationHref("/qr/stats", hrefs)).not.toBe("/qr");
  });

  it("keeps non-QR parent routes working", () => {
    expect(resolveActiveNavigationHref("/timetable/class-12")).toBe("/timetable");
    expect(resolveActiveNavigationHref("/")).toBe("/");
  });
});
