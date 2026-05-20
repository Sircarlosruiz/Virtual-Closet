import { test, expect } from "@playwright/test";

test.describe("Login de mayorista", () => {
  test("login exitoso redirige a dashboard", async ({ page }) => {
    const timestamp = Date.now();
    const email = `login-${timestamp}@test.com`;

    await page.goto("/registro");
    await page.getByLabel("Nombre del negocio").fill(`Login Test ${timestamp}`);
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Contraseña").fill("password123");
    await page.getByRole("button", { name: "Crear cuenta" }).click();
    await expect(page).toHaveURL(/.*dashboard\/onboarding/);

    await page.context().clearCookies();
    await page.goto("/login");
    await expect(page.locator('[data-slot="card-title"]')).toHaveText("Iniciar sesión");

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Contraseña").fill("password123");
    await page.getByRole("button", { name: "Iniciar sesión" }).click();

    await expect(page).toHaveURL(/.*dashboard/);
  });

  test("muestra error genérico con credenciales incorrectas", async ({ page }) => {
    await page.goto("/login");

    await page.getByLabel("Email").fill("nonexistent@test.com");
    await page.getByLabel("Contraseña").fill("wrongpassword");
    await page.getByRole("button", { name: "Iniciar sesión" }).click();

    await expect(page.getByText("Email o contraseña incorrectos")).toBeVisible();
  });

  test("link a registro funciona", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("link", { name: "Regístrate gratis" }).click();
    await expect(page).toHaveURL(/.*registro/);
  });

  test("usuario autenticado no puede acceder a login", async ({ page }) => {
    const timestamp = Date.now();
    await page.goto("/registro");
    await page.getByLabel("Nombre del negocio").fill(`Auth Test ${timestamp}`);
    await page.getByLabel("Email").fill(`auth-${timestamp}@test.com`);
    await page.getByLabel("Contraseña").fill("password123");
    await page.getByRole("button", { name: "Crear cuenta" }).click();

    await expect(page).toHaveURL(/.*dashboard\/onboarding/);

    await page.goto("/login");
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test("acceso a dashboard sin autenticación redirige a login", async ({ page }) => {
    await page.context().clearCookies();
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/.*login/);
  });
});
