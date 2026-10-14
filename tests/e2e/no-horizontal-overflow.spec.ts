import { expect, test } from "@playwright/test";

for (const path of ["/", "/overview", "/sources", "/timetable", "/content", "/changes", "/notifications"]) {
  test(`no page-level horizontal overflow on ${path}`, async ({ page }) => {
    await page.goto(path);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
}
