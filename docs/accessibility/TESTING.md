# Accessibility Testing Guide

This guide covers manual and automated testing procedures for WCAG 2.1 AA compliance in Open-WebUI.

---

## Prerequisites

### Required Tools

```bash
# Install axe-core CLI
npm install -g @axe-core/cli

# Install Lighthouse (if not already installed)
npm install -g lighthouse

# Install Playwright (for automated tests)
npm install -D @playwright/test
```

### Optional Screen Readers

**Linux:**
```bash
sudo apt install orca
```

**macOS:**
VoiceOver is built-in (Cmd+F5 to toggle)

**Windows:**
- Download NVDA: https://www.nvaccess.org/download/

---

## Manual Testing Procedures

### 1. Keyboard Navigation Test

**Goal:** Verify all functionality is accessible via keyboard without mouse.

**Steps:**
1. Unplug your mouse (or don't use it)
2. Open Open-WebUI: http://localhost:3000 or https://chat.spooty.io
3. Press `Tab` to begin keyboard navigation

**Checklist:**

#### Skip-to-Content Link
- [ ] First `Tab` reveals skip-to-content link at top of page
- [ ] Skip link has visible focus indicator (2px solid blue outline)
- [ ] Pressing `Enter` on skip link jumps to main chat interface
- [ ] Focus moves to first interactive element in main content

#### Focus Indicators
- [ ] All buttons have visible focus indicator when tabbed to
- [ ] All links have visible focus indicator
- [ ] All form inputs have visible focus indicator
- [ ] Focus indicator is at least 2px solid outline
- [ ] Focus indicator has sufficient contrast (3:1 against background)
- [ ] Focus indicator visible in both light and dark modes

#### Modal Dialogs
- [ ] `Tab` through modal traps focus inside modal
- [ ] Cannot tab to elements behind modal
- [ ] `Escape` key closes modal
- [ ] Focus returns to trigger element after modal closes
- [ ] Modal has proper ARIA labels (check with screen reader)

#### Sidebar
- [ ] Sidebar can be opened with keyboard (via button)
- [ ] `Escape` key closes sidebar
- [ ] First interactive element in sidebar receives focus on open
- [ ] Tab order in sidebar is logical

#### Message Input
- [ ] Can tab to message input field
- [ ] `Enter` sends message (or `Ctrl+Enter` depending on settings)
- [ ] `Shift+Enter` creates new line
- [ ] `Escape` stops AI response
- [ ] `↑` (up arrow) when input empty edits last message
- [ ] All toolbar buttons (attach, tools, settings) reachable via Tab

#### Navigation
- [ ] Can navigate entire chat history via keyboard
- [ ] Can switch between chats via keyboard
- [ ] Can access settings via keyboard
- [ ] Can logout via keyboard

**Pass Criteria:** All interactive elements reachable and operable via keyboard.

---

### 2. Color Contrast Test

**Goal:** Verify all text and UI components meet WCAG AA color contrast requirements.

**Tools:**
- axe DevTools Chrome Extension
- WebAIM Contrast Checker

**Steps:**

#### Using axe DevTools (Recommended)

1. Install axe DevTools:
   - Chrome: https://chrome.google.com/webstore/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd
   - Firefox: https://addons.mozilla.org/en-US/firefox/addon/axe-devtools/

2. Open Open-WebUI in browser

3. Open DevTools (F12) → axe tab

4. Click "Scan ALL of my page"

5. Review "Color Contrast" violations:
   - Filter by "WCAG AA" level
   - Note all elements with insufficient contrast
   - Document: element, current ratio, required ratio

6. Fix violations using WebAIM Contrast Checker:
   - https://webaim.org/resources/contrastchecker/
   - Enter foreground and background colors
   - Adjust colors until meeting 4.5:1 (normal text) or 3:1 (large text)

#### Manual Spot Checks

Test these common problem areas:

- [ ] Gray text on light backgrounds (e.g., `.text-gray-500`)
- [ ] Placeholder text in inputs
- [ ] Disabled button text
- [ ] Link colors in dark mode
- [ ] Icon colors (especially gray icons)
- [ ] Badge/pill background and text
- [ ] Alert/toast notification text

**Pass Criteria:**
- Normal text: 4.5:1 contrast ratio minimum
- Large text (18pt+ or 14pt+ bold): 3:1 contrast ratio minimum
- UI components (buttons, inputs): 3:1 contrast ratio minimum

---

### 3. Screen Reader Test

**Goal:** Verify content is properly announced and navigable for screen reader users.

#### Linux (Orca)

```bash
# Start Orca
orca --enable=speech

# Navigate with keyboard
# Orca will announce focused elements
```

**Test Checklist:**

##### Landmarks
- [ ] "Skip to main content" link announced first
- [ ] Main landmark announced ("main region" or "Chat interface")
- [ ] Navigation landmarks announced (if present)
- [ ] Complementary landmarks announced for sidebars

##### Interactive Elements
- [ ] All buttons announce their label or purpose
- [ ] Icon-only buttons have meaningful aria-labels
- [ ] Links announce link text and destination (if href visible)
- [ ] Form inputs announce label and current value
- [ ] Checkboxes announce label and checked state

##### Modal Dialogs
- [ ] Modal opening is announced
- [ ] Modal title announced via aria-labelledby
- [ ] Focus moves into modal
- [ ] Can navigate modal content with arrow keys
- [ ] Closing modal is announced
- [ ] Focus returns to trigger element

##### Dynamic Content
- [ ] New chat messages announced (via ARIA live region)
- [ ] Loading states announced ("Loading..." or spinner announced)
- [ ] Error messages announced when they appear
- [ ] Success messages announced when they appear

##### Headings
- [ ] Can navigate by headings (h1, h2, h3, etc.)
- [ ] Heading levels are hierarchical (no skipped levels)
- [ ] Headings describe the section content

##### Forms
- [ ] All input fields have associated labels
- [ ] Required fields announced as required
- [ ] Invalid fields announced with error messages
- [ ] Error messages associated with fields (aria-describedby)

**Pass Criteria:** All content and functionality accessible and understandable via screen reader.

---

### 4. Zoom and Text Resize Test

**Goal:** Verify content remains usable at 200% zoom.

**Steps:**

1. Open Open-WebUI in browser

2. Zoom to 200% (Ctrl + "+" or Cmd + "+")

**Checklist:**
- [ ] All text remains readable (no truncation)
- [ ] No horizontal scrolling required (or minimal)
- [ ] All functionality still accessible
- [ ] Buttons remain clickable/tappable
- [ ] Modal dialogs fit within viewport
- [ ] Form inputs remain usable
- [ ] Layout doesn't break or overlap

3. Test text-only zoom (browser setting):
   - Firefox: View → Zoom → Zoom Text Only
   - Chrome: Settings → Appearance → Font size

**Pass Criteria:** All content accessible and functional at 200% zoom.

---

## Automated Testing

### 1. Lighthouse Accessibility Audit

**Command:**
```bash
# Local development
lighthouse http://localhost:3000 \
  --only-categories=accessibility \
  --output=html \
  --output-path=./lighthouse-local.html

# Staging
lighthouse https://chat-staging.spooty.io \
  --only-categories=accessibility \
  --output=html \
  --output-path=./lighthouse-staging.html

# Production
lighthouse https://chat.spooty.io \
  --only-categories=accessibility \
  --output=html \
  --output-path=./lighthouse-prod.html
```

**Interpreting Results:**

- **Score 90-100:** Excellent, WCAG AA compliant
- **Score 50-89:** Needs improvement
- **Score 0-49:** Critical issues, not compliant

**Focus Areas:**
- Names and labels
- Contrast
- ARIA attributes
- Keyboard navigation
- Semantic HTML

**Target:** 90+ score before April 24, 2026 deadline

---

### 2. axe-core CLI Scan

**Command:**
```bash
# Scan local development
npx axe --chrome-options="headless" http://localhost:3000 \
  --save axe-results.json

# Scan specific page
npx axe --chrome-options="headless" http://localhost:3000/chat/abc123 \
  --save axe-chat-results.json

# Scan multiple URLs (create urls.txt with one URL per line)
npx axe --chrome-options="headless" \
  --load-urls=urls.txt \
  --save axe-multi-results.json
```

**Analyze Results:**
```bash
# Total violations
jq '.violations | length' axe-results.json

# Critical violations only
jq '.violations[] | select(.impact=="critical")' axe-results.json

# Color contrast violations
jq '.violations[] | select(.id=="color-contrast")' axe-results.json

# Button name violations (icon buttons without aria-label)
jq '.violations[] | select(.id=="button-name")' axe-results.json

# ARIA attribute violations
jq '.violations[] | select(.id | startswith("aria-"))' axe-results.json
```

**Target:** 0 critical violations before April 24, 2026 deadline

---

### 3. Playwright Accessibility Tests

**Setup:**
```bash
# Install Playwright
npm install -D @playwright/test

# Install browsers
npx playwright install
```

**Example Test: Keyboard Navigation**
```typescript
// tests/accessibility/keyboard-navigation.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Keyboard Navigation', () => {
  test('skip to content link is visible on first tab', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Press Tab
    await page.keyboard.press('Tab');

    // Skip link should be visible
    const skipLink = page.locator('.skip-to-content');
    await expect(skipLink).toBeVisible();
    await expect(skipLink).toBeFocused();
  });

  test('skip to content link jumps to main content', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Tab to skip link
    await page.keyboard.press('Tab');

    // Press Enter
    await page.keyboard.press('Enter');

    // Focus should be on main content area
    const mainContent = page.locator('#main-content');
    await expect(mainContent).toBeFocused();
  });

  test('all interactive elements have visible focus', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Get all buttons, links, inputs
    const interactiveElements = await page.locator(
      'button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ).all();

    for (const element of interactiveElements) {
      await element.focus();

      // Check focus is visible (outline or box-shadow)
      const outlineWidth = await element.evaluate(el =>
        window.getComputedStyle(el).outlineWidth
      );
      const boxShadow = await element.evaluate(el =>
        window.getComputedStyle(el).boxShadow
      );

      expect(
        outlineWidth !== '0px' || boxShadow !== 'none'
      ).toBeTruthy();
    }
  });

  test('modal closes with Escape key', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Open a modal (adjust selector as needed)
    await page.click('[data-testid="open-settings"]');

    // Modal should be visible
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // Press Escape
    await page.keyboard.press('Escape');

    // Modal should be closed
    await expect(modal).not.toBeVisible();
  });
});
```

**Example Test: Screen Reader Support**
```typescript
// tests/accessibility/screen-reader.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Screen Reader Support', () => {
  test('all buttons have accessible names', async ({ page }) => {
    await page.goto('http://localhost:3000');

    const buttons = await page.locator('button').all();

    for (const button of buttons) {
      // Get accessible name (aria-label, aria-labelledby, or text content)
      const ariaLabel = await button.getAttribute('aria-label');
      const ariaLabelledBy = await button.getAttribute('aria-labelledby');
      const textContent = await button.textContent();

      const accessibleName = ariaLabel ||
        (ariaLabelledBy && await page.locator(`#${ariaLabelledBy}`).textContent()) ||
        textContent?.trim();

      expect(accessibleName).toBeTruthy();
      expect(accessibleName).not.toBe('');
    }
  });

  test('all images have alt text', async ({ page }) => {
    await page.goto('http://localhost:3000');

    const images = await page.locator('img').all();

    for (const image of images) {
      const alt = await image.getAttribute('alt');
      expect(alt).not.toBeNull();
      // Alt can be empty for decorative images
    }
  });

  test('form inputs have labels', async ({ page }) => {
    await page.goto('http://localhost:3000');

    const inputs = await page.locator('input, textarea, select').all();

    for (const input of inputs) {
      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledBy = await input.getAttribute('aria-labelledby');

      // Must have aria-label, aria-labelledby, or associated <label>
      const hasLabel = ariaLabel || ariaLabelledBy ||
        (id && await page.locator(`label[for="${id}"]`).count() > 0);

      expect(hasLabel).toBeTruthy();
    }
  });

  test('main landmarks are present', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Should have main landmark
    const main = page.locator('main, [role="main"]');
    await expect(main).toBeVisible();

    // Should have aria-label or aria-labelledby
    const mainAriaLabel = await main.getAttribute('aria-label');
    const mainAriaLabelledBy = await main.getAttribute('aria-labelledby');
    expect(mainAriaLabel || mainAriaLabelledBy).toBeTruthy();
  });
});
```

**Run Tests:**
```bash
# Run all accessibility tests
npx playwright test tests/accessibility/

# Run specific test file
npx playwright test tests/accessibility/keyboard-navigation.spec.ts

# Run with UI mode (recommended for debugging)
npx playwright test --ui

# Run in headed mode (see browser)
npx playwright test --headed
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/accessibility-tests.yml
name: Accessibility Tests

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [feat/wcag-*]

jobs:
  lighthouse:
    runs-on: stax-browser
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Build and serve
        run: |
          npm run build
          npm run preview &
          sleep 10

      - name: Run Lighthouse
        run: |
          npm install -g lighthouse
          lighthouse http://localhost:4173 \
            --only-categories=accessibility \
            --output=json \
            --output-path=lighthouse-results.json

      - name: Check Lighthouse score
        run: |
          SCORE=$(jq '.categories.accessibility.score * 100' lighthouse-results.json)
          echo "Accessibility score: $SCORE"
          if [ $(echo "$SCORE < 90" | bc) -eq 1 ]; then
            echo "Accessibility score below 90, failing build"
            exit 1
          fi

      - name: Upload Lighthouse report
        uses: actions/upload-artifact@v3
        with:
          name: lighthouse-report
          path: lighthouse-results.json

  axe-scan:
    runs-on: stax-browser
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Build and serve
        run: |
          npm run build
          npm run preview &
          sleep 10

      - name: Run axe scan
        run: |
          npm install -g @axe-core/cli
          npx axe --chrome-options="headless" http://localhost:4173 \
            --save axe-results.json

      - name: Check for critical violations
        run: |
          CRITICAL=$(jq '[.violations[] | select(.impact=="critical")] | length' axe-results.json)
          echo "Critical violations: $CRITICAL"
          if [ $CRITICAL -gt 0 ]; then
            echo "Critical accessibility violations found, failing build"
            jq '.violations[] | select(.impact=="critical")' axe-results.json
            exit 1
          fi

      - name: Upload axe report
        uses: actions/upload-artifact@v3
        with:
          name: axe-report
          path: axe-results.json

  playwright-tests:
    runs-on: stax-browser
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps

      - name: Run Playwright accessibility tests
        run: npx playwright test tests/accessibility/

      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

---

## Validation Checklist

Before declaring WCAG 2.1 AA compliance complete:

### Automated Tests
- [ ] Lighthouse score 90+ on all pages
- [ ] axe-core 0 critical violations on all pages
- [ ] Playwright accessibility tests passing (100%)
- [ ] CI/CD accessibility tests passing

### Manual Tests
- [ ] Full keyboard navigation test passed
- [ ] Screen reader test passed (Orca/NVDA/VoiceOver)
- [ ] Color contrast audit completed (0 violations)
- [ ] 200% zoom test passed
- [ ] Reduced motion preference respected

### Documentation
- [ ] Accessibility documentation complete
- [ ] Keyboard shortcuts documented
- [ ] Testing procedures documented
- [ ] Known issues documented (if any)

### Deployment
- [ ] Staging environment validated
- [ ] Production deployment plan reviewed
- [ ] Rollback plan documented
- [ ] Accessibility features announced to users

---

## Troubleshooting

### Common Issues

**Issue:** Lighthouse score varies between runs
- **Solution:** Run multiple times, use median score
- **Cause:** Performance can affect score

**Issue:** axe-core finds violations Lighthouse doesn't
- **Solution:** Fix all axe-core violations first
- **Cause:** axe-core is more comprehensive

**Issue:** Screen reader announces unexpected content
- **Solution:** Check ARIA labels, hidden elements
- **Cause:** Improper use of aria-hidden or sr-only

**Issue:** Focus trapped in wrong element
- **Solution:** Review focus-trap configuration
- **Cause:** Nested modals or improper focus management

---

## Next Steps

After completing P0-1 (keyboard navigation):

1. **P0-2: Color Contrast Fixes** (2-3 days)
   - Run axe DevTools scan
   - Fix all color contrast violations
   - Validate with WebAIM Contrast Checker

2. **P0-3: Screen Reader Support** (2 days)
   - Add ARIA landmarks throughout app
   - Add ARIA labels to all icon buttons
   - Add ARIA live regions for dynamic content
   - Test with Orca/NVDA/VoiceOver

3. **Final Validation** (April 18-24)
   - Run all automated tests
   - Complete all manual tests
   - Document remaining issues
   - Deploy to production
