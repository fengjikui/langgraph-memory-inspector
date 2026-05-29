import { expect, test } from "@playwright/test";

test("diagnostic click opens writes and highlights the related channel", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("LangGraph Memory Inspector")).toBeVisible();
  const diagnosticCard = page.getByRole("button", { name: /conflicting_residence_memory extract_profile/i });
  await expect(diagnosticCard).toBeVisible();

  await diagnosticCard.click();

  await expect(page.getByRole("button", { name: /Writes/i })).toHaveClass(/active/);
  await expect(page.getByText("Looking for writes to")).toBeVisible();
  await expect(page.locator(".write-row.focused")).toContainText("state.memory_events");
});
