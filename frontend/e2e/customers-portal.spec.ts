import { test, expect } from "@playwright/test";

async function registerAndLogin(page: any, timestamp: number) {
  const email = `customer-e2e-${timestamp}@test.com`;
  await page.goto("/registro");
  await page.getByLabel("Nombre del negocio").fill(`Customer E2E ${timestamp}`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Contraseña").fill("password123");
  await page.getByRole("button", { name: "Crear cuenta" }).click();
  await expect(page).toHaveURL(/.*dashboard\/onboarding/);
  return email;
}

test.describe("Customer Management UI", () => {
  test.beforeEach(async ({ page }) => {
    const timestamp = Date.now();
    await registerAndLogin(page, timestamp);
  });

  test.describe("Customer List Page", () => {
    test("shows empty state when no customers exist", async ({ page }) => {
      await page.goto("/dashboard/customers");
      await expect(page.getByText("No tienes clientes aún")).toBeVisible();
      await expect(page.getByText("Registrar tu primer cliente")).toBeVisible();
    });

    test("registers a new customer via modal", async ({ page }) => {
      await page.goto("/dashboard/customers");
      await page.getByRole("button", { name: "Registrar cliente" }).click();

      await expect(page.getByText("Registrar cliente")).toBeVisible();
      await page.getByLabel("Nombre").fill("Ana López");
      await page.getByLabel("Email").fill("ana@buyer.com");
      await page.getByRole("button", { name: "Registrar" }).click();

      await expect(page.getByText("Ana López")).toBeVisible();
      await expect(page.getByText("ana@buyer.com")).toBeVisible();
      await expect(page.getByText("Invitado")).toBeVisible();
    });

    test("shows validation error for invalid email", async ({ page }) => {
      await page.goto("/dashboard/customers");
      await page.getByRole("button", { name: "Registrar cliente" }).click();

      await page.getByLabel("Email").fill("not-an-email");
      await page.getByRole("button", { name: "Registrar" }).click();

      await expect(page.getByText("Email inválido")).toBeVisible();
    });

    test("shows error for duplicate email", async ({ page }) => {
      await page.goto("/dashboard/customers");
      await page.getByRole("button", { name: "Registrar cliente" }).click();
      await page.getByLabel("Nombre").fill("Ana López");
      await page.getByLabel("Email").fill("duplicate@test.com");
      await page.getByRole("button", { name: "Registrar" }).click();

      await page.getByRole("button", { name: "Registrar cliente" }).click();
      await page.getByLabel("Nombre").fill("Ana Again");
      await page.getByLabel("Email").fill("duplicate@test.com");
      await page.getByRole("button", { name: "Registrar" }).click();

      await expect(page.getByText("Este email ya está registrado")).toBeVisible();
    });
  });
});

test.describe("Buyer Portal UI", () => {
  test("shows request link page", async ({ page }) => {
    await page.goto("/portal/request-link");
    await expect(page.getByText("Solicitar nuevo enlace")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByRole("button", { name: "Enviar enlace" })).toBeVisible();
  });

  test("shows validation for request link form", async ({ page }) => {
    await page.goto("/portal/request-link");
    await page.getByLabel("Email").fill("not-an-email");
    await page.getByRole("button", { name: "Enviar enlace" }).click();
    await expect(page.getByText("Email inválido")).toBeVisible();
  });

  test("portal auth page shows error without token", async ({ page }) => {
    await page.goto("/portal/auth");
    await expect(page.getByText("Token no proporcionado")).toBeVisible();
    await expect(page.getByRole("button", { name: "Solicitar nuevo enlace" })).toBeVisible();
  });

  test("portal auth page shows error with invalid token", async ({ page }) => {
    await page.goto("/portal/auth?token=invalid_token_string");
    await expect(page.getByText(/Token inválido|Error/)).toBeVisible();
  });
});
