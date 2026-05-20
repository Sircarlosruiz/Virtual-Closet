import { test, expect } from "@playwright/test";

test.describe("Registro de mayorista", () => {
  test("registro exitoso redirige a onboarding", async ({ page }) => {
    await page.goto("/registro");

    await expect(page.locator('[data-slot="card-title"]')).toHaveText("Crear cuenta");

    const timestamp = Date.now();
    await page.getByLabel("Nombre del negocio").fill(`Test Business ${timestamp}`);
    await page.getByLabel("Email").fill(`e2e-${timestamp}@test.com`);
    await page.getByLabel("Contraseña").fill("password123");

    await page.getByRole("button", { name: "Crear cuenta" }).click();

    await expect(page).toHaveURL(/.*dashboard\/onboarding/);
    await expect(page.getByText("Tus primeras 5 prendas son gratis")).toBeVisible();
  });

  test("muestra error si contraseña es menor a 8 caracteres", async ({ page }) => {
    await page.goto("/registro");

    await page.getByLabel("Nombre del negocio").fill("Test Business");
    await page.getByLabel("Email").fill("short@test.com");
    await page.getByLabel("Contraseña").fill("123");

    await page.getByRole("button", { name: "Crear cuenta" }).click();

    await expect(page.getByText("La contraseña debe tener al menos 8 caracteres")).toBeVisible();
  });

  test("muestra error si email ya está registrado", async ({ page }) => {
    const timestamp = Date.now();
    const email = `dup-${timestamp}@test.com`;

    await page.goto("/registro");
    await page.getByLabel("Nombre del negocio").fill("First Business");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Contraseña").fill("password123");
    await page.getByRole("button", { name: "Crear cuenta" }).click();

    await expect(page).toHaveURL(/.*dashboard\/onboarding/);

    await page.context().clearCookies();
    await page.goto("/registro");
    await page.getByLabel("Nombre del negocio").fill("Second Business");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Contraseña").fill("password456");
    await page.getByRole("button", { name: "Crear cuenta" }).click();

    await expect(page.getByText("Este email ya está registrado")).toBeVisible();
  });

  test("usuario autenticado no puede acceder a registro", async ({ page }) => {
    const timestamp = Date.now();
    await page.goto("/registro");
    await page.getByLabel("Nombre del negocio").fill(`Redirect Test ${timestamp}`);
    await page.getByLabel("Email").fill(`redirect-${timestamp}@test.com`);
    await page.getByLabel("Contraseña").fill("password123");
    await page.getByRole("button", { name: "Crear cuenta" }).click();

    await expect(page).toHaveURL(/.*dashboard\/onboarding/);

    await page.goto("/registro");
    await expect(page).toHaveURL(/.*dashboard/);
  });
});
