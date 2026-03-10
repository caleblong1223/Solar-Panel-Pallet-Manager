import { expect, test, type Page, type Route } from "@playwright/test";

type BarcodeSearchResponse = {
  query: string;
  exact: boolean;
  total: number;
  results: Array<Record<string, unknown>>;
};

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function openBuilderAndStartPallet(page: Page) {
  await page.goto("/builder");
  await page.getByRole("button", { name: "Start new pallet" }).click();
  await expect(page.getByText(/Active pallet/i)).toBeVisible();
}

function seedCachedPallet(page: Page, serial: string, palletNumber: number, status = "completed") {
  return page.addInitScript(
    ([cachedSerial, cachedPalletNumber, cachedStatus]) => {
      localStorage.setItem(
        "pm2_local_pallets",
        JSON.stringify([
          {
            id: 42,
            pallet_number: cachedPalletNumber,
            status: cachedStatus,
            template_type: "450WT",
            max_panels: 25,
            customer_id: null,
            created_by: null,
            completed_by: null,
            created_at: "2026-03-10T12:00:00.000Z",
            completed_at: cachedStatus === "completed" ? "2026-03-10T12:15:00.000Z" : null,
            deleted_at: null,
            item_count: 1,
            items: [
              {
                id: 4200,
                serial: cachedSerial,
                slot_index: 1,
                added_by: null,
                added_at: "2026-03-10T12:05:00.000Z",
              },
            ],
          },
        ])
      );
    },
    [serial, palletNumber, status] as const
  );
}

async function wireDefaultBuilderRoutes(page: Page) {
  await page.route(/\/api\/v1\/customers\?.*/, (route) => fulfillJson(route, { total: 0, customers: [] }));
}

test("blocks scan immediately when API reports the serial on another pallet", async ({ page }) => {
  await wireDefaultBuilderRoutes(page);
  await page.route(/\/api\/v1\/barcodes\/search.*/, (route) =>
    fulfillJson(route, {
      query: "CRS-DUPLICATE-1",
      exact: true,
      total: 1,
      results: [
        {
          source: "pallet_item",
          serial: "CRS-DUPLICATE-1",
          matched_exact: true,
          pallet_id: 700,
          pallet_number: 88,
          pallet_status: "completed",
          slot_index: 4,
          customer_id: null,
          created_at: "2026-03-10T12:00:00.000Z",
        },
      ],
    } satisfies BarcodeSearchResponse)
  );

  await openBuilderAndStartPallet(page);
  await page.getByLabel("Scan barcode").fill("CRS-DUPLICATE-1");
  await page.getByRole("button", { name: "Add" }).click();

  await expect(page.getByRole("heading", { name: "Duplicate detected" })).toBeVisible();
  await expect(page.getByText("Panel is already on a pallet.")).toBeVisible();
  await expect(page.getByText("Pallet #88")).toBeVisible();
  await expect(page.getByText("CRS-DUPLICATE-1")).toBeVisible();
  await expect(page.getByText("Items on pallet")).toHaveCount(0);
});

test("uses cached local pallets for duplicate detection when barcode lookup is offline", async ({ page }) => {
  await seedCachedPallet(page, "CRS-OFFLINE-1", 77, "completed");
  await wireDefaultBuilderRoutes(page);
  await page.route(/\/api\/v1\/barcodes\/search.*/, async (route) => {
    await route.abort("failed");
  });

  await openBuilderAndStartPallet(page);
  await page.getByLabel("Scan barcode").fill("CRS-OFFLINE-1");
  await page.getByRole("button", { name: "Add" }).click();

  await expect(page.getByRole("heading", { name: "Duplicate detected" })).toBeVisible();
  await expect(page.getByText("Pallet #77")).toBeVisible();
  await expect(page.getByText("CRS-OFFLINE-1")).toBeVisible();
  await expect(page.getByText("Items on pallet")).toHaveCount(0);
});

test("still adds a non-duplicate serial after duplicate check passes", async ({ page }) => {
  await wireDefaultBuilderRoutes(page);
  await page.route(/\/api\/v1\/barcodes\/search.*/, (route) =>
    fulfillJson(route, {
      query: "CRS-OK-1",
      exact: true,
      total: 1,
      results: [
        {
          source: "sim_panel",
          serial: "CRS-OK-1",
          matched_exact: true,
          sim_panel_id: 111,
          sim_batch_id: 9,
          sim_test_timestamp: "2026-03-10T12:00:00.000Z",
          sim_panel_type: "450WT",
          sim_result: "PASS",
          sim_watts: 450.1,
          created_at: "2026-03-10T12:00:00.000Z",
        },
      ],
    } satisfies BarcodeSearchResponse)
  );

  await openBuilderAndStartPallet(page);
  await page.getByLabel("Scan barcode").fill("CRS-OK-1");
  await page.getByRole("button", { name: "Add" }).click();

  await expect(page.getByText("Added")).toBeVisible();
  await expect(page.getByText("Items on pallet")).toBeVisible();
  await expect(page.getByText("CRS-OK-1")).toBeVisible();
});

test("shows duplicate modal and preserves the draft when finalize hits a stale server conflict", async ({ page }) => {
  let searchCount = 0;

  await wireDefaultBuilderRoutes(page);
  await page.route(/\/api\/v1\/barcodes\/search.*/, (route) => {
    searchCount += 1;
    const response: BarcodeSearchResponse =
      searchCount === 1
        ? {
            query: "CRS-RACE-1",
            exact: true,
            total: 1,
            results: [
              {
                source: "sim_panel",
                serial: "CRS-RACE-1",
                matched_exact: true,
                sim_panel_id: 222,
                sim_batch_id: 9,
                sim_test_timestamp: "2026-03-10T12:00:00.000Z",
                sim_panel_type: "450WT",
                sim_result: "PASS",
                sim_watts: 449.9,
                created_at: "2026-03-10T12:00:00.000Z",
              },
            ],
          }
        : {
            query: "CRS-RACE-1",
            exact: true,
            total: 1,
            results: [
              {
                source: "pallet_item",
                serial: "CRS-RACE-1",
                matched_exact: true,
                pallet_id: 701,
                pallet_number: 99,
                pallet_status: "active",
                slot_index: 2,
                customer_id: null,
                created_at: "2026-03-10T12:20:00.000Z",
              },
            ],
          };
    return fulfillJson(route, response);
  });
  await page.route(/\/api\/v1\/pallets$/, async (route) => {
    if (route.request().method() !== "POST") {
      await fulfillJson(route, { total: 0, pallets: [] });
      return;
    }
    await fulfillJson(route, {
      id: 501,
      pallet_number: 1,
      status: "active",
      template_type: "200WT",
      max_panels: 25,
      customer_id: null,
      created_by: null,
      completed_by: null,
      created_at: "2026-03-10T12:30:00.000Z",
      completed_at: null,
      deleted_at: null,
      item_count: 0,
      items: [],
    }, 201);
  });
  await page.route(/\/api\/v1\/pallets\/501\/items$/, async (route) => {
    await route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({
        detail: {
          error_code: "SERIAL_ALREADY_ASSIGNED_ELSEWHERE",
          message: "Serial already assigned to another pallet",
        },
      }),
    });
  });
  await page.route(/\/api\/v1\/pallets\/501$/, async (route) => {
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 204, body: "" });
      return;
    }
    await route.fallback();
  });

  await openBuilderAndStartPallet(page);
  await page.getByLabel("Scan barcode").fill("CRS-RACE-1");
  await page.getByRole("button", { name: "Add" }).click();
  await expect(page.locator("li", { hasText: "CRS-RACE-1" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Complete pallet" })).toBeEnabled();

  await page.getByRole("button", { name: "Complete pallet" }).click();

  await expect(page.getByRole("heading", { name: "Duplicate detected" })).toBeVisible();
  await expect(page.getByText("Pallet #99")).toBeVisible();
  await expect(page.getByText("Serial: CRS-RACE-1")).toBeVisible();
  await expect(page.getByText("Items on pallet")).toBeVisible();
});
