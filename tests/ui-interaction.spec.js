const { test, expect } = require('@playwright/test');
const path = require('path');

test.use({
  viewport: { width: 1600, height: 900 },
});

test('resizable panels keep the 3D viewport and properties panel usable', async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto('http://localhost:8080', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    localStorage.removeItem('brepExplorerSidebarWidth');
    localStorage.removeItem('brepExplorerPanelWidth');
  });
  await page.reload({ waitUntil: 'domcontentloaded' });

  await page.locator('#fileInput').setInputFiles(
    path.join(process.cwd(), 'uploads', '100106_7f144e5b_0000_0001.step')
  );
  await expect(page.locator('#status')).toContainText(/faces/i, { timeout: 30000 });

  const layout = async () => page.evaluate(() => {
    const box = (selector) => {
      const rect = document.querySelector(selector).getBoundingClientRect();
      return {
        left: rect.left,
        right: rect.right,
        width: rect.width,
        height: rect.height,
      };
    };

    return {
      sidebar: box('.sidebar'),
      main: box('.main'),
      panel: box('.panel'),
      canvas: box('#canvas'),
      viewportWidth: window.innerWidth,
    };
  });

  const dragBy = async (selector, deltaX) => {
    const rect = await page.locator(selector).boundingBox();
    const startX = rect.x + rect.width / 2;
    const y = rect.y + 20;
    await page.mouse.move(startX, y);
    await page.mouse.down();
    await page.mouse.move(startX + deltaX, y, { steps: 12 });
    await page.mouse.up();
    await page.waitForTimeout(100);
  };

  let before = await layout();
  expect(before.panel.width).toBeGreaterThanOrEqual(260);
  expect(before.canvas.width).toBeGreaterThanOrEqual(400);

  await dragBy('#sidebarResizer', 240);
  let afterSidebar = await layout();
  expect(afterSidebar.sidebar.width).toBeGreaterThan(before.sidebar.width);
  expect(afterSidebar.canvas.width).toBeLessThan(before.canvas.width);
  expect(Math.abs(afterSidebar.canvas.width - afterSidebar.main.width)).toBeLessThanOrEqual(1);
  expect(afterSidebar.canvas.width).toBeGreaterThanOrEqual(400);
  expect(afterSidebar.panel.width).toBeGreaterThanOrEqual(260);
  expect(Math.abs(afterSidebar.panel.right - afterSidebar.viewportWidth)).toBeLessThanOrEqual(1);

  await dragBy('#panelResizer', -160);
  let afterPanel = await layout();
  expect(afterPanel.panel.width).toBeGreaterThan(afterSidebar.panel.width);
  expect(afterPanel.canvas.width).toBeLessThan(afterSidebar.canvas.width);
  expect(Math.abs(afterPanel.canvas.width - afterPanel.main.width)).toBeLessThanOrEqual(1);
  expect(afterPanel.canvas.width).toBeGreaterThanOrEqual(400);
  expect(afterPanel.main.right).toBeLessThanOrEqual(afterPanel.panel.left + 1);

  const selectedText = async () => {
    const selected = page.locator('.tree-item.selected');
    return await selected.count() ? await selected.first().textContent() : '';
  };

  const selectedBeforeDrag = await selectedText();
  const canvas = await page.locator('#canvas').boundingBox();
  await page.mouse.move(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2);
  await page.mouse.down();
  await page.mouse.move(canvas.x + canvas.width / 2 + 140, canvas.y + canvas.height / 2 + 40, { steps: 12 });
  await page.mouse.up();
  const selectedAfterDrag = await selectedText();
  expect(selectedAfterDrag).toBe(selectedBeforeDrag);

  await page.screenshot({ path: 'test-results/ui-layout-after-resize.png', fullPage: true });
});
