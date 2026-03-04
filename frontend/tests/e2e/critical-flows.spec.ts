import { test, expect } from "@playwright/test";

test("app root loads", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
});

