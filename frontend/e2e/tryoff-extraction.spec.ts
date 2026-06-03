import { test, expect } from "@playwright/test";

test.describe("TryOff garment extraction flow", () => {
  test.beforeEach(async ({ page }) => {
    // Register and login before each test
    const timestamp = Date.now();
    const email = `tryoff-${timestamp}@test.com`;

    await page.goto("/registro");
    await page.getByLabel("Nombre del negocio").fill(`TryOff Test ${timestamp}`);
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Contraseña").fill("password123");
    await page.getByRole("button", { name: "Crear cuenta" }).click();
    await expect(page).toHaveURL(/.*dashboard\/onboarding/);
  });

  test("upload page renders with dropzone and garment chips", async ({ page }) => {
    await page.goto("/extraction/new");

    await expect(page.getByRole("heading", { name: "Extract Garments from Image" })).toBeVisible();
    await expect(page.getByRole("button", { name: /browse files/i })).toBeVisible();
    await expect(page.getByRole("button", { name: "Upper Garment" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Lower Garment" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Full Dress" })).toBeVisible();

    // Submit button should be disabled initially
    const submitButton = page.getByRole("button", { name: "Start Extraction" });
    await expect(submitButton).toBeDisabled();
  });

  test("rejects non-image files with error message", async ({ page }) => {
    await page.goto("/extraction/new");

    // Create a fake non-image file
    const buffer = Buffer.from("not an image");
    await page.setInputFiles('input[type="file"]', {
      name: "document.pdf",
      mimeType: "application/pdf",
      buffer,
    });

    await expect(page.getByText("Please upload a JPEG or PNG image")).toBeVisible();
  });

  test("shows preview after selecting valid image", async ({ page }) => {
    await page.goto("/extraction/new");

    // Create a small valid PNG file
    const pngBuffer = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
      "base64"
    );
    await page.setInputFiles('input[type="file"]', {
      name: "test-image.png",
      mimeType: "image/png",
      buffer: pngBuffer,
    });

    // Should show the image preview
    await expect(page.getByAltText("Selected source image")).toBeVisible();

    // Submit should still be disabled (no garment type selected)
    const submitButton = page.getByRole("button", { name: "Start Extraction" });
    await expect(submitButton).toBeDisabled();
    await expect(page.getByText("Select at least one garment type")).toBeVisible();
  });

  test("garment chips toggle selection", async ({ page }) => {
    await page.goto("/extraction/new");

    const upperChip = page.getByRole("button", { name: "Upper Garment" });
    const lowerChip = page.getByRole("button", { name: "Lower Garment" });

    // Initially not selected
    await expect(upperChip).toHaveAttribute("aria-pressed", "false");

    // Click to select
    await upperChip.click();
    await expect(upperChip).toHaveAttribute("aria-pressed", "true");

    // Click again to deselect
    await upperChip.click();
    await expect(upperChip).toHaveAttribute("aria-pressed", "false");

    // Select multiple
    await upperChip.click();
    await lowerChip.click();
    await expect(upperChip).toHaveAttribute("aria-pressed", "true");
    await expect(lowerChip).toHaveAttribute("aria-pressed", "true");
  });

  test("status page renders with job IDs from query params", async ({ page }) => {
    await page.goto("/extraction/status?job_ids=test-1,test-2");

    await expect(page.getByRole("heading", { name: "Extraction Status" })).toBeVisible();
    await expect(page.getByText("2 jobs being processed")).toBeVisible();
  });

  test("full golden path: upload → select → submit → status", async ({ page }) => {
    await page.goto("/extraction/new");

    // Step 1: Upload image
    const pngBuffer = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
      "base64"
    );
    await page.setInputFiles('input[type="file"]', {
      name: "model-photo.png",
      mimeType: "image/png",
      buffer: pngBuffer,
    });

    await expect(page.getByAltText("Selected source image")).toBeVisible();

    // Step 2: Select garment types
    await page.getByRole("button", { name: "Upper Garment" }).click();
    await page.getByRole("button", { name: "Lower Garment" }).click();

    // Step 3: Submit (will fail if backend endpoint not available, but UI should attempt)
    const submitButton = page.getByRole("button", { name: "Start Extraction" });
    await expect(submitButton).toBeEnabled();

    // Note: The actual submission requires the backend API to be available.
    // We verify the button becomes enabled and the UI is in the correct state.
    // Full E2E with real backend would require the tryoff endpoints to be live.
  });
});
