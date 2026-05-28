import { test, expect } from "@playwright/test";

async function registerAndLogin(page: any, timestamp: number) {
  const email = `catalog-e2e-${timestamp}@test.com`;
  await page.goto("/registro");
  await page.getByLabel("Nombre del negocio").fill(`Catalog E2E ${timestamp}`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña").fill("password123");
  await page.getByRole("button", { name: "Crear cuenta" }).click();
  await expect(page).toHaveURL(/.*dashboard\/onboarding/);
  return email;
}

test.describe("Catalog Management UI", () => {
  test.beforeEach(async ({ page }) => {
    const timestamp = Date.now();
    await registerAndLogin(page, timestamp);
  });

  test.describe("Catalog List Page", () => {
    test("shows empty state when no catalogs exist", async ({ page }) => {
      await page.goto("/dashboard/catalogos");
      await expect(page.getByText("No tienes catálogos aún")).toBeVisible();
      await expect(page.getByText("Crear tu primer catálogo")).toBeVisible();
    });

    test("creates a new catalog via modal", async ({ page }) => {
      await page.goto("/dashboard/catalogos");
      await page.getByRole("button", { name: "Crear catálogo" }).click();

      await expect(page.getByText("Crear nuevo catálogo")).toBeVisible();
      await page.getByLabel("Nombre").fill("Summer Collection 2026");
      await page.getByRole("button", { name: "Crear" }).click();

      await expect(page.getByText("Summer Collection 2026")).toBeVisible();
      await expect(page.getByText("Borrador")).toBeVisible();
      await expect(page.getByText("0 prendas")).toBeVisible();
    });

    test("shows validation error for empty catalog name", async ({ page }) => {
      await page.goto("/dashboard/catalogos");
      await page.getByRole("button", { name: "Crear catálogo" }).click();

      await page.getByLabel("Nombre").fill("");
      await page.getByRole("button", { name: "Crear" }).click();

      await expect(page.getByText("El nombre es obligatorio")).toBeVisible();
    });

    test("navigates to catalog detail when clicking a catalog", async ({ page }) => {
      await page.goto("/dashboard/catalogos");
      await page.getByRole("button", { name: "Crear catálogo" }).click();
      await page.getByLabel("Nombre").fill("Test Catalog");
      await page.getByRole("button", { name: "Crear" }).click();

      await page.getByText("Test Catalog").click();
      await expect(page).toHaveURL(/.*dashboard\/catalogos\/[a-f0-9-]+/);
    });
  });

  test.describe("Catalog Detail Page", () => {
    test("shows empty state for new catalog", async ({ page }) => {
      await page.goto("/dashboard/catalogos");
      await page.getByRole("button", { name: "Crear catálogo" }).click();
      await page.getByLabel("Nombre").fill("Empty Catalog");
      await page.getByRole("button", { name: "Crear" }).click();

      await page.getByText("Empty Catalog").click();
      await expect(page.getByText("Este catálogo está vacío")).toBeVisible();
    });

    test("edits catalog name inline", async ({ page }) => {
      await page.goto("/dashboard/catalogos");
      await page.getByRole("button", { name: "Crear catálogo" }).click();
      await page.getByLabel("Nombre").fill("Old Name");
      await page.getByRole("button", { name: "Crear" }).click();

      await page.getByText("Old Name").click();
      await expect(page).toHaveURL(/.*dashboard\/catalogos\/[a-f0-9-]+/);

      await page.getByRole("button", { name: "Añadir primera prenda" }).click();
      await expect(page.getByText("Este catálogo está vacío")).toBeVisible();
    });

    test("publish button is disabled for empty catalog", async ({ page }) => {
      await page.goto("/dashboard/catalogos");
      await page.getByRole("button", { name: "Crear catálogo" }).click();
      await page.getByLabel("Nombre").fill("Empty Catalog");
      await page.getByRole("button", { name: "Crear" }).click();

      await page.getByText("Empty Catalog").click();
      await expect(page.getByRole("button", { name: "Publicar" })).toBeDisabled();
    });

    test("deletes catalog with confirmation", async ({ page }) => {
      await page.goto("/dashboard/catalogos");
      await page.getByRole("button", { name: "Crear catálogo" }).click();
      await page.getByLabel("Nombre").fill("Delete Me");
      await page.getByRole("button", { name: "Crear" }).click();

      await page.getByText("Delete Me").click();
      await page.getByRole("button", { name: "Eliminar" }).click();

      await expect(page.getByText("Eliminar catálogo")).toBeVisible();
      await page.getByRole("button", { name: "Eliminar" }).nth(1).click();

      await expect(page).toHaveURL(/.*dashboard\/catalogos/);
      await expect(page.getByText("Delete Me")).not.toBeVisible();
    });
  });
});
