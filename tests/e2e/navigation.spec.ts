import { expect, test } from "@playwright/test";

test("today is the default home page", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Today's Timetable" })).toBeVisible();
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Timetable shortcuts" })).toBeVisible();
  await expect(page.locator("body")).not.toHaveCSS("overflow-x", "scroll");
});

test("primary sections can be opened", async ({ page, isMobile }) => {
  await page.goto("/");
  const navigation = isMobile
    ? page.getByRole("navigation", { name: "Mobile primary navigation" })
    : page.getByRole("navigation", { name: "Primary navigation" });
  await navigation.getByRole("link", { name: /Weekly Timetable|Timetable/i }).click();
  await expect(page).toHaveURL(/\/timetable/);
  await expect(page.getByRole("heading", { name: /Weekly Timetable|Timetable/i })).toBeVisible();
});

test("global search opens learning content", async ({ page }) => {
  await page.goto("/");
  const search = page.getByRole("textbox", { name: "Search videos, PDFs, subjects and topics" });
  await search.fill("Economics PDF");
  await search.press("Enter");
  await expect(page).toHaveURL(/\/content\?q=Economics\+PDF/);
});

test("touch targets remain usable on phones and tablets", async ({ page }) => {
  await page.goto("/content");
  const search = page.getByRole("textbox", { name: "Search learning content" });
  await expect(search).toBeVisible();
  const box = await search.boundingBox();
  expect(box?.height ?? 0).toBeGreaterThanOrEqual(30);
});

test("keyboard navigation reaches main content", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});

test("daily changes explains what the page means", async ({ page }) => {
  await page.goto("/changes");
  await expect(page.getByRole("heading", { name: "What Changed?" })).toBeVisible();
  await expect(page.getByText("Timetable", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Video or PDF", { exact: true })).toBeVisible();
});

test("content search accepts a pasted link", async ({ page }) => {
  await page.goto("/content");
  const search = page.getByRole("textbox", { name: "Search learning content" });
  await search.fill("https://drive.google.com/file/d/example/view");
  await search.press("Enter");
  await expect(page).toHaveURL(/q=https%3A%2F%2Fdrive\.google\.com/);
});


test("universal timetable groups classes by time", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Universal view", { exact: true })).toBeVisible();
  await expect(page.getByText("One row for each start time", { exact: false })).toBeVisible();
});

test("one-word multilingual content search is accepted", async ({ page }) => {
  await page.goto("/content");
  const search = page.getByRole("textbox", { name: "Search learning content" });
  await search.fill("प्रकाश");
  await search.press("Enter");
  await expect(page).toHaveURL(/q=%E0%A4%AA%E0%A5%8D%E0%A4%B0%E0%A4%95%E0%A4%BE%E0%A4%B6/);
});
