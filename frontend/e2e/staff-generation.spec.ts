import { test, expect } from '@playwright/test';

test.describe('Staff generation UI access', () => {
  test('unauthenticated visitors are sent to login', async ({ page }) => {
    await page.goto('/staff/generation');
    await expect(page).toHaveURL(/login/);
  });

  test('mayorista does not see generation controls or private copy', async ({ page }) => {
    const timestamp = Date.now();
    await page.goto('/registro');
    await page.getByLabel('Nombre del negocio').fill(`Mayorista ${timestamp}`);
    await page.getByLabel('Email').fill(`mayorista-${timestamp}@test.com`);
    await page.getByLabel('Contraseña').fill('password123');
    await page.getByRole('button', { name: 'Crear cuenta' }).click();
    await expect(page).toHaveURL(/dashboard/);

    await page.goto('/staff/generation');
    await expect(page.getByText('No autorizado')).toBeVisible();
    await expect(
      page.getByText(/reservada al staff/i),
    ).toBeVisible();
    await expect(page.getByRole('button', { name: 'Iniciar generación' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Generación IA' })).toHaveCount(0);
    await expect(page.getByText(/prompt|plantilla|openai/i)).toHaveCount(0);
  });
});
