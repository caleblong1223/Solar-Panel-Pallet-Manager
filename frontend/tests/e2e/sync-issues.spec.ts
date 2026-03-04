import { test, expect, type Page } from "@playwright/test";

function seedOfflineSessionAndOutbox(page: Page) {
  return page.addInitScript(() => {
    localStorage.setItem(
      "pm2_cached_user",
      JSON.stringify({
        id: 9001,
        username: "offline_operator",
        email: "offline@example.com",
        is_active: true,
        roles: [{ id: 1, name: "packout_operator" }],
      })
    );
    localStorage.removeItem("pm2_access_token");
    localStorage.setItem(
      "pm2_sync_outbox",
      JSON.stringify([
        {
          op_id: "op-needs-review-1",
          op_type: "pallet.item_add",
          payload: { pallet_id: 1, serial: "SERIAL-A" },
          created_at: "2026-03-04T12:00:00.000Z",
          attempt_count: 1,
          last_error: "Serial already assigned to another pallet",
          last_error_code: "SERIAL_ALREADY_ASSIGNED_ELSEWHERE",
          next_retry_at: null,
          state: "needs_review",
        },
        {
          op_id: "op-pending-1",
          op_type: "pallet.complete",
          payload: { pallet_id: 2 },
          created_at: "2026-03-04T12:01:00.000Z",
          attempt_count: 2,
          last_error: "Network timeout",
          last_error_code: null,
          next_retry_at: "2099-01-01T00:00:00.000Z",
          state: "pending",
        },
      ])
    );
  });
}

test("sync issues page renders review and pending buckets", async ({ page }) => {
  await seedOfflineSessionAndOutbox(page);
  await page.goto("/sync-issues");

  await expect(page.getByRole("heading", { name: /Sync Issues/i })).toBeVisible();
  await expect(page.getByText(/Needs Review \(1\)/)).toBeVisible();
  await expect(page.getByText(/Pending Errors \(1\)/)).toBeVisible();
  await expect(page.getByText(/Serial already exists on another pallet/i)).toBeVisible();
});

test("discard removes operation from sync issues list", async ({ page }) => {
  await seedOfflineSessionAndOutbox(page);
  await page.goto("/sync-issues");

  const row = page.locator("li", { hasText: "op-needs-review-1" });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Discard" }).click();
  await expect(row).toHaveCount(0);
});
