import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const routeSource = readFileSync(new URL("../app/q/[slug]/route.ts", import.meta.url), "utf8");
const builderSource = readFileSync(new URL("../app/qr/page.tsx", import.meta.url), "utf8");
const statsSource = readFileSync(new URL("../app/qr/stats/page.tsx", import.meta.url), "utf8");

describe("QR scan experience contracts", () => {
  it("keeps email and Wi-Fi controls available over full-page artwork", () => {
    expect(routeSource).toContain('const controlLayer =');
    expect(routeSource).toContain('shellClass === "scanPageImage" ? "pageControls" : "scanControls"');
    expect(routeSource).toContain('${visual}${controlLayer}');
    expect(routeSource).toContain('${emailBlock}');
    expect(routeSource).toContain('${wifiBlock}');
  });

  it("does not silently bypass failed tracked analytics", () => {
    expect(routeSource).toContain('confirmWithRetry');
    expect(routeSource).toContain('trackingError');
    expect(routeSource).toContain('Continue without tracking');
  });

  it("defaults Wi-Fi creation to direct auto-connect semantics", () => {
    expect(builderSource).toContain('if(next==="wifi"){setTrackingMode("direct")');
    expect(builderSource).toContain('Auto-connect Wi-Fi');
    expect(builderSource).toContain('Tracked Wi-Fi');
  });

  it("keeps a reusable Brand Kit for repeated QR generation", () => {
    expect(builderSource).toContain('tti_qr_brand_kit_v1');
    expect(builderSource).toContain('Save current as default');
    expect(builderSource).toContain('Create another with same design');
  });

  it("keeps technical device telemetry collapsed by default", () => {
    expect(statsSource).toContain('qr-device-details-v23');
    expect(statsSource).toContain('<details className="qr-device-details-v23">');
    expect(statsSource).toContain('Technical details');
  });
});
