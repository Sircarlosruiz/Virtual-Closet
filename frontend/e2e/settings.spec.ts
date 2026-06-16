import { test, expect } from "@playwright/test";

test.describe("Buyer Catalog Access", () => {
  test("access page renders without token", async ({ page }) => {
    await page.goto("/portal/access");

    await expect(
      page.getByRole("heading", { name: "Sin token de acceso" })
    ).toBeVisible();

    await expect(
      page.getByText("Contactá al mayorista para recibir acceso")
    ).toBeVisible();
  });

  test("access page shows loading state", async ({ page }) => {
    await page.goto("/portal/access?token=test-token");

    // Should show loading spinner
    await expect(page.getByText("Validando enlace...")).toBeVisible();
  });

  test("access page shows expired link error", async ({ page }) => {
    // Without a valid backend, the API will fail
    // This tests the error handling path
    await page.goto("/portal/access?token=expired-token");

    // After API failure, should show error state
    await expect(
      page.getByText("Error al validar el enlace")
    ).toBeVisible();

    await expect(
      page.getByRole("link", { name: "Solicitar nuevo enlace" })
    ).toBeVisible();
  });
});

test.describe("Account Settings", () => {
  test("settings account page requires authentication", async ({ page }) => {
    await page.goto("/settings/account");

    // Should redirect to login
    await expect(page).toHaveURL(/.*login/);
  });

  test("settings account page shows admin list for authenticated user", async ({ page }) => {
    const timestamp = Date.now();
    await page.goto("/registro");
    await page.getByLabel("Nombre del negocio").fill(`Settings Test ${timestamp}`);
    await page.getByLabel("Email").fill(`settings-${timestamp}@test.com`);
    await page.getByLabel("Contraseña").fill("password123");
    await page.getByRole("button", { name: "Crear cuenta" }).click();

    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to settings
    await page.goto("/settings/account");

    await expect(page).toHaveURL(/.*settings\/account/);

    // Should show business info
    await expect(
      page.getByRole("heading", { name: "Información del negocio" })
    ).toBeVisible();

    // Should show admin management
    await expect(
      page.getByRole("heading", { name: "Administradores" })
    ).toBeVisible();

    // Should show invite form
    await expect(
      page.getByPlaceholder("Email del nuevo admin")
    ).toBeVisible();

    await expect(
      page.getByRole("button", { name: "Invitar admin" })
    ).toBeVisible();
  });
});

test.describe("Buyer Links Settings", () => {
  test("buyer links page requires authentication", async ({ page }) => {
    await page.goto("/settings/buyer-links");

    // Should redirect to login
    await expect(page).toHaveURL(/.*login/);
  });

  test("buyer links page shows generator for authenticated user", async ({ page }) => {
    const timestamp = Date.now();
    await page.goto("/registro");
    await page.getByLabel("Nombre del negocio").fill(`BuyerLinks Test ${timestamp}`);
    await page.getByLabel("Email").fill(`buyerlinks-${timestamp}@test.com`);
    await page.getByLabel("Contraseña").fill("password123");
    await page.getByRole("button", { name: "Crear cuenta" }).click();

    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to buyer links settings
    await page.goto("/settings/buyer-links");

    await expect(page).toHaveURL(/.*settings\/buyer-links/);

    // Should show generator form
    await expect(
      page.getByRole("heading", { name: "Generar nuevo enlace" })
    ).toBeVisible();

    // Should show catalog selection
    await expect(page.getByText("Catálogos")).toBeVisible();

    // Should show TTL input
    await expect(page.getByLabel("Duración (días)")).toBeVisible();

    // Should show generate button
    await expect(
      page.getByRole("button", { name: "Generar enlace" })
    ).toBeVisible();

    // Should show link history section
    await expect(
      page.getByRole("heading", { name: "Enlaces generados" })
    ).toBeVisible();
  });
});

test.describe("Settings Navigation", () => {
  test("settings layout shows navigation tabs", async ({ page }) => {
    const timestamp = Date.now();
    await page.goto("/registro");
    await page.getByLabel("Nombre del negocio").fill(`Nav Test ${timestamp}`);
    await page.getByLabel("Email").fill(`nav-${timestamp}@test.com`);
    await page.getByLabel("Contraseña").fill("password123");
    await page.getByRole("button", { name: "Crear cuenta" }).click();

    await expect(page).toHaveURL(/.*dashboard/);

    await page.goto("/settings/account");

    // Should show settings navigation
    await expect(page.getByRole("heading", { name: "Configuración" })).toBeVisible();

    // Should have navigation tabs
    await expect(page.getByRole("link", { name: "Cuenta y admins" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Enlaces de comprador" })).toBeVisible();
  });
});
