# Directive: Writing Frontend Tests

> **Pattern type:** Quality assurance
> **Complexity:** Low-Medium
> **Files touched:** 1-3

---

## Prerequisites

- `TESTING_STRATEGY.md` — Overall test philosophy
- `ADR_002_sveltekit_frontend.md` — Frontend architecture

---

## Structural Pattern

Frontend tests use Vitest for unit tests and Playwright for E2E:

1. **Unit tests** for stores and utilities
2. **Component tests** for Svelte components
3. **E2E tests** for user journeys

| Test Type | Tool | Location |
|-----------|------|----------|
| Unit tests | Vitest | `tests/unit/` |
| Component | Vitest + Testing Library | `tests/unit/components/` |
| E2E tests | Playwright | `tests/e2e/` |

---

## Illustrative Application

### Step 1: Unit Test for Store Logic

```typescript
// tests/unit/stores/features.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { features, addFeature, removeFeature, resetFeatures } from '$lib/stores';

describe('features store', () => {
  beforeEach(() => {
    // Reset store before each test
    resetFeatures();
  });

  it('should start empty', () => {
    const value = get(features);
    expect(value).toEqual([]);
  });

  it('should add a feature', () => {
    addFeature({ id: '1', name: 'Test Feature', enabled: true });

    const value = get(features);
    expect(value).toHaveLength(1);
    expect(value[0].name).toBe('Test Feature');
  });

  it('should remove a feature by id', () => {
    addFeature({ id: '1', name: 'Feature 1', enabled: true });
    addFeature({ id: '2', name: 'Feature 2', enabled: true });

    removeFeature('1');

    const value = get(features);
    expect(value).toHaveLength(1);
    expect(value[0].id).toBe('2');
  });

  it('should handle removing non-existent feature', () => {
    addFeature({ id: '1', name: 'Feature 1', enabled: true });

    removeFeature('non-existent');

    const value = get(features);
    expect(value).toHaveLength(1);
  });
});
```

### Step 2: Unit Test for Utility Functions

```typescript
// tests/unit/utils/formatting.test.ts
import { describe, it, expect } from 'vitest';
import { formatDate, formatBytes, truncateText } from '$lib/utils/formatting';

describe('formatDate', () => {
  it('should format timestamp to readable date', () => {
    const timestamp = 1704067200; // 2024-01-01 00:00:00 UTC
    const result = formatDate(timestamp);

    expect(result).toContain('2024');
    expect(result).toContain('Jan');
  });

  it('should handle null timestamp', () => {
    const result = formatDate(null);
    expect(result).toBe('—');
  });
});

describe('formatBytes', () => {
  it('should format bytes to KB', () => {
    expect(formatBytes(1024)).toBe('1 KB');
  });

  it('should format bytes to MB', () => {
    expect(formatBytes(1048576)).toBe('1 MB');
  });

  it('should handle zero', () => {
    expect(formatBytes(0)).toBe('0 Bytes');
  });
});

describe('truncateText', () => {
  it('should truncate long text', () => {
    const text = 'This is a very long text that should be truncated';
    const result = truncateText(text, 20);

    expect(result.length).toBeLessThanOrEqual(23); // 20 + '...'
    expect(result).toContain('...');
  });

  it('should not truncate short text', () => {
    const text = 'Short';
    const result = truncateText(text, 20);

    expect(result).toBe('Short');
  });
});
```

### Step 3: Component Test

```typescript
// tests/unit/components/FeatureCard.test.ts
import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import FeatureCard from '$lib/components/FeatureCard.svelte';

describe('FeatureCard', () => {
  const mockFeature = {
    id: '1',
    name: 'Test Feature',
    description: 'A test feature description',
    enabled: true,
  };

  it('should render feature name', () => {
    const { getByText } = render(FeatureCard, {
      props: { feature: mockFeature }
    });

    expect(getByText('Test Feature')).toBeTruthy();
  });

  it('should render feature description', () => {
    const { getByText } = render(FeatureCard, {
      props: { feature: mockFeature }
    });

    expect(getByText('A test feature description')).toBeTruthy();
  });

  it('should show enabled status', () => {
    const { getByTestId } = render(FeatureCard, {
      props: { feature: mockFeature }
    });

    const toggle = getByTestId('feature-toggle');
    expect(toggle).toBeChecked();
  });

  it('should call onToggle when clicked', async () => {
    const onToggle = vi.fn();
    const { getByTestId } = render(FeatureCard, {
      props: { feature: mockFeature, onToggle }
    });

    const toggle = getByTestId('feature-toggle');
    await fireEvent.click(toggle);

    expect(onToggle).toHaveBeenCalledWith('1', false);
  });

  it('should call onDelete when delete button clicked', async () => {
    const onDelete = vi.fn();
    const { getByTestId } = render(FeatureCard, {
      props: { feature: mockFeature, onDelete }
    });

    const deleteBtn = getByTestId('delete-button');
    await fireEvent.click(deleteBtn);

    expect(onDelete).toHaveBeenCalledWith('1');
  });
});
```

### Step 4: E2E Test with Playwright

```typescript
// tests/e2e/feature-management.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Feature Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/auth');
    await page.fill('[data-testid="email-input"]', 'admin@test.com');
    await page.fill('[data-testid="password-input"]', 'password');
    await page.click('[data-testid="login-button"]');

    // Wait for dashboard
    await page.waitForURL('/');
  });

  test('should display feature list', async ({ page }) => {
    await page.goto('/admin/features');

    // Wait for features to load
    await page.waitForSelector('[data-testid="feature-list"]');

    // Check list is visible
    const featureList = page.locator('[data-testid="feature-list"]');
    await expect(featureList).toBeVisible();
  });

  test('should create a new feature', async ({ page }) => {
    await page.goto('/admin/features');

    // Click add button
    await page.click('[data-testid="add-feature-button"]');

    // Fill form
    await page.fill('[data-testid="feature-name-input"]', 'New E2E Feature');
    await page.fill('[data-testid="feature-description-input"]', 'Created by E2E test');

    // Submit
    await page.click('[data-testid="save-feature-button"]');

    // Verify feature appears in list
    await expect(page.locator('text=New E2E Feature')).toBeVisible();
  });

  test('should toggle feature enabled state', async ({ page }) => {
    await page.goto('/admin/features');

    // Find first feature toggle
    const toggle = page.locator('[data-testid="feature-toggle"]').first();
    const initialState = await toggle.isChecked();

    // Click toggle
    await toggle.click();

    // Verify state changed
    await expect(toggle).toHaveAttribute(
      'aria-checked',
      (!initialState).toString()
    );
  });

  test('should delete a feature', async ({ page }) => {
    await page.goto('/admin/features');

    // Get initial count
    const initialCount = await page.locator('[data-testid="feature-card"]').count();

    // Click delete on first feature
    await page.click('[data-testid="delete-button"]');

    // Confirm deletion
    await page.click('[data-testid="confirm-delete-button"]');

    // Verify count decreased
    await expect(page.locator('[data-testid="feature-card"]')).toHaveCount(
      initialCount - 1
    );
  });
});
```

### Step 5: Test Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte({ hot: !process.env.VITEST })],
  test: {
    include: ['tests/unit/**/*.{test,spec}.{js,ts}'],
    environment: 'jsdom',
    globals: true,
    setupFiles: ['tests/setup.ts'],
  },
  resolve: {
    alias: {
      $lib: '/src/lib',
    },
  },
});
```

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev',
    port: 5173,
    reuseExistingServer: !process.env.CI,
  },
});
```

---

## Transfer Prompt

**When you need to write frontend tests:**

1. **For store logic:**
   ```typescript
   // tests/unit/stores/{store}.test.ts
   import { get } from 'svelte/store';
   import { myStore } from '$lib/stores';

   it('should handle action', () => {
     myStore.doAction();
     expect(get(myStore)).toBe(expected);
   });
   ```

2. **For utility functions:**
   ```typescript
   // tests/unit/utils/{util}.test.ts
   import { myUtil } from '$lib/utils';

   it('should transform input', () => {
     expect(myUtil(input)).toBe(expected);
   });
   ```

3. **For components:**
   ```typescript
   // tests/unit/components/{Component}.test.ts
   import { render, fireEvent } from '@testing-library/svelte';
   import Component from '$lib/components/Component.svelte';

   it('should render props', () => {
     const { getByText } = render(Component, { props: { title: 'Test' } });
     expect(getByText('Test')).toBeTruthy();
   });
   ```

4. **For E2E journeys:**
   ```typescript
   // tests/e2e/{feature}.spec.ts
   import { test, expect } from '@playwright/test';

   test('user can complete action', async ({ page }) => {
     await page.goto('/page');
     await page.click('[data-testid="button"]');
     await expect(page.locator('[data-testid="result"]')).toBeVisible();
   });
   ```

5. **Run tests:**
   ```bash
   # Unit tests
   npm run test

   # E2E tests
   npm run test:e2e
   ```

**Test data attributes:**
- Add `data-testid="unique-id"` to elements for reliable selection
- Prefer data-testid over CSS selectors for stability

**Signals that this pattern applies:**
- Adding new store or utility
- Creating new component
- Implementing user-facing feature
- Fixing UI bug (write regression test)

---

## Related Documents

- `TESTING_STRATEGY.md` — Test philosophy
- `DIRECTIVE_writing_backend_tests.md` — Backend tests
- `DIRECTIVE_creating_svelte_store.md` — Store patterns

---

*Last updated: 2026-02-03*
