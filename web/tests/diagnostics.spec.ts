import { expect, test } from "@playwright/test";

test("diagnostic click opens writes and highlights the related channel", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("LangGraph Memory Inspector")).toBeVisible();
  await expect(page.getByLabel("Active namespace")).toHaveValue("relocation_policy_agent");

  await page.getByLabel("Active namespace").selectOption("shadow_replay");
  await expect(page.getByText("Shadow replay initialized")).toBeVisible();
  await expect(page.getByText("Shadow replay profile check")).toBeVisible();

  await page.getByLabel("Active namespace").selectOption("relocation_policy_agent");
  await expect(page.getByText("3-5 of 5")).toBeVisible();
  await page.getByRole("button", { name: /Load earlier checkpoints/i }).click();
  await expect(page.getByText("1-5 of 5")).toBeVisible();
  await expect(page.getByText("Thread initialized")).toBeVisible();

  const diagnosticCard = page.getByRole("button", { name: /conflicting_residence_memory extract_profile/i });
  await expect(diagnosticCard).toBeVisible();

  await diagnosticCard.click();

  await expect(page.getByRole("button", { name: /Writes/i })).toHaveClass(/active/);
  await expect(page.getByText("Looking for writes to")).toBeVisible();
  await expect(page.locator(".write-row.focused")).toContainText("state.memory_events");

  await expect(page.getByLabel("Redact private fields")).toBeChecked();
  await page.getByRole("button", { name: /Export redacted/i }).click();

  await expect(page.getByText("Debug bundle exported")).toBeVisible();
  const exportResult = page.locator(".export-result");
  await expect(exportResult.getByText(/exports\/lgmi-debug-/)).toBeVisible();
  await expect(exportResult.getByText(/21\.4 KB/)).toBeVisible();
  await expect(exportResult.getByText(/conflicting_residence_memory/)).toBeVisible();
  await expect(exportResult.getByText(/Redaction:/)).toBeVisible();
  await expect(exportResult.getByText(/redacted/)).toBeVisible();

  await page.getByLabel("State path filter").fill("state.memory_events");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByText("1-1 of 1")).toBeVisible();
  await expect(page.getByText("Move to Hangzhou appended")).toBeVisible();
});
