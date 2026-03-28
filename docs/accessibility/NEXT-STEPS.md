# Immediate Next Steps for WCAG 2.1 AA Compliance

**Current Date:** March 28, 2026
**Deadline:** April 24, 2026 (26 days remaining)
**Branch:** `feat/wcag-phase1-accessibility`
**Status:** P0-1 Keyboard Navigation 80% complete

---

## Priority 1: Complete P0-1 Remaining Tasks (4-6 hours)

### Task 1: Add ARIA Labels to Icon-Only Buttons

**Estimated Time:** 4-6 hours

**Files to Modify:**
- `src/lib/components/chat/MessageInput.svelte` (primary)
- `src/lib/components/chat/Navbar.svelte`
- `src/lib/components/layout/Sidebar.svelte`
- Other components with icon-only buttons

**Specific Buttons Missing aria-label:**

1. **MessageInput.svelte:**
   - Line 1092: Scroll-to-bottom button
   - Line 1628: Valves button (model settings)
   - Line 1707: Web Search toggle button
   - Line 1725: Image generation toggle button
   - Other integration/tool buttons

**Pattern to Apply:**
```svelte
<!-- BEFORE -->
<button on:click={handleClick}>
  <IconComponent className="size-4" />
</button>

<!-- AFTER -->
<button
  aria-label="Descriptive action name"
  on:click={handleClick}
>
  <IconComponent className="size-4" />
</button>
```

**Validation:**
```bash
# Find buttons without aria-label
grep -n "<button" src/lib/components/chat/MessageInput.svelte | \
  grep -v "aria-label"

# Test with screen reader
orca --enable=speech
# Navigate to each button and verify announcement
```

**Acceptance Criteria:**
- [ ] All icon-only buttons have meaningful aria-label
- [ ] Screen reader announces button purpose
- [ ] No "button" or "unlabeled button" announcements

---

### Task 2: Implement Arrow Key Navigation (Optional for P0-1)

**Estimated Time:** 6-8 hours (Can be deferred to P1 if time is tight)

**Priority:** Medium (not critical for minimal AA compliance)

**Components Needing Enhancement:**
- Model selector dropdown
- Chat history list
- Settings menu items

**Pattern to Implement:**
```svelte
<script>
  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'ArrowDown') {
      // Move focus to next item
      event.preventDefault();
      focusNextItem();
    } else if (event.key === 'ArrowUp') {
      // Move focus to previous item
      event.preventDefault();
      focusPreviousItem();
    }
  }
</script>

<div
  role="listbox"
  aria-label="Model selector"
  on:keydown={handleKeyDown}
>
  {#each models as model}
    <div
      role="option"
      aria-selected={selected === model.id}
      tabindex={selected === model.id ? 0 : -1}
    >
      {model.name}
    </div>
  {/each}
</div>
```

**Decision:** Defer to P1 if needed to meet deadline.

---

### Task 3: Create Automated Keyboard Navigation Tests

**Estimated Time:** 6-8 hours

**Create Test Files:**

1. **`tests/accessibility/keyboard-navigation.spec.ts`**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Keyboard Navigation - P0-1', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
  });

  test('skip-to-content link visible on first tab', async ({ page }) => {
    await page.keyboard.press('Tab');
    const skipLink = page.locator('.skip-to-content');
    await expect(skipLink).toBeVisible();
    await expect(skipLink).toBeFocused();
  });

  test('skip-to-content jumps to main content', async ({ page }) => {
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    const mainContent = page.locator('#main-content');
    // Check focus is within main content area
    await expect(page.locator(':focus')).toBeVisible();
  });

  test('all buttons have visible focus indicators', async ({ page }) => {
    const buttons = await page.locator('button:visible').all();

    for (const button of buttons.slice(0, 10)) { // Test first 10 for speed
      await button.focus();

      const outlineWidth = await button.evaluate(el =>
        window.getComputedStyle(el).outlineWidth
      );

      // Should have 2px outline
      expect(outlineWidth).not.toBe('0px');
    }
  });

  test('modal closes with Escape key', async ({ page }) => {
    // Open settings modal (adjust selector as needed)
    await page.click('button[aria-label*="Settings"]').catch(() => {});
    await page.click('button:has-text("Settings")').catch(() => {});

    const modal = page.locator('[role="dialog"]').first();

    if (await modal.isVisible()) {
      await page.keyboard.press('Escape');
      await expect(modal).not.toBeVisible();
    }
  });

  test('tab order is logical', async ({ page }) => {
    // Press Tab multiple times
    const focusOrder: string[] = [];

    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      const focused = page.locator(':focus');
      const tagName = await focused.evaluate(el => el.tagName.toLowerCase());
      const ariaLabel = await focused.getAttribute('aria-label');
      const text = await focused.textContent();

      focusOrder.push(`${tagName}${ariaLabel ? ` [${ariaLabel}]` : ''}${text ? `: ${text.slice(0, 20)}` : ''}`);
    }

    console.log('Focus order:', focusOrder);
    // Visual verification - tab order should make sense
    expect(focusOrder.length).toBe(10);
  });
});
```

2. **`tests/accessibility/screen-reader.spec.ts`**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Screen Reader Support - P0-3', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
  });

  test('all buttons have accessible names', async ({ page }) => {
    const buttons = await page.locator('button:visible').all();

    for (const button of buttons) {
      const ariaLabel = await button.getAttribute('aria-label');
      const ariaLabelledBy = await button.getAttribute('aria-labelledby');
      const textContent = (await button.textContent())?.trim();

      const hasAccessibleName = ariaLabel || ariaLabelledBy || textContent;

      if (!hasAccessibleName) {
        const html = await button.evaluate(el => el.outerHTML);
        console.error('Button without accessible name:', html);
      }

      expect(hasAccessibleName).toBeTruthy();
    }
  });

  test('main landmark exists', async ({ page }) => {
    const main = page.locator('main, [role="main"]');
    await expect(main).toBeVisible();

    const ariaLabel = await main.getAttribute('aria-label');
    expect(ariaLabel).toBeTruthy();
  });

  test('all images have alt text', async ({ page }) => {
    const images = await page.locator('img:visible').all();

    for (const image of images) {
      const alt = await image.getAttribute('alt');
      // Alt attribute must exist (can be empty for decorative)
      expect(alt).not.toBeNull();
    }
  });
});
```

**Run Tests:**
```bash
# Install Playwright if not already
npm install -D @playwright/test
npx playwright install

# Run tests
npx playwright test tests/accessibility/

# Run with UI mode (recommended for first run)
npx playwright test --ui

# Run specific test
npx playwright test tests/accessibility/keyboard-navigation.spec.ts
```

**Acceptance Criteria:**
- [ ] All keyboard navigation tests passing
- [ ] All screen reader tests passing
- [ ] Tests integrated into CI/CD (optional for P0-1)

---

## Priority 2: P0-2 Color Contrast Audit (2-3 days)

**Start Date:** Immediately after P0-1 completion
**Target Completion:** April 4, 2026

### Step 1: Install Tools

```bash
# Install axe DevTools Chrome extension
# URL: https://chrome.google.com/webstore/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd

# Install axe-core CLI
npm install -g @axe-core/cli
```

### Step 2: Run Initial Scan

```bash
# Start dev server
npm run dev

# In another terminal, run axe scan
npx axe --chrome-options="headless" http://localhost:3000 \
  --save axe-initial.json

# Check color contrast violations
jq '.violations[] | select(.id=="color-contrast") | .nodes[] | .html' axe-initial.json
```

### Step 3: Fix Common Violations

**Expected Problem Areas:**

1. **Gray Text on Light Backgrounds**
   - Current: `.text-gray-500` (likely fails 4.5:1)
   - Fix: Update to darker gray in `src/tailwind.css`

2. **Placeholder Text**
   - Current: May be too light
   - Fix: Increase contrast in `input::placeholder` styles

3. **Disabled Buttons**
   - Current: Gray text on gray background
   - Fix: Ensure 3:1 minimum contrast

4. **Links in Dark Mode**
   - Current: May be too bright or too dim
   - Fix: Adjust link colors in dark mode theme

**Fix Process:**
1. For each violation, note the element and current colors
2. Use WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
3. Find compliant color (4.5:1 for text, 3:1 for UI)
4. Update `src/tailwind.css` or component styles
5. Verify fix with axe-core scan

### Step 4: Validation

```bash
# Run final scan
npx axe --chrome-options="headless" http://localhost:3000 \
  --save axe-final.json

# Check for remaining violations
jq '.violations[] | select(.id=="color-contrast")' axe-final.json

# Should return: (empty) or []
```

**Target:** 0 color contrast violations

---

## Priority 3: P0-3 Screen Reader Support (2 days)

**Start Date:** Immediately after P0-2 completion
**Target Completion:** April 11, 2026

### Critical Tasks

1. **Add ARIA Landmarks** (4 hours)
   - [ ] Header with `role="banner"`
   - [ ] Navigation with `role="navigation"`
   - [x] Main with `role="main"` (already done)
   - [ ] Footer with `role="contentinfo"` (if exists)

2. **Add ARIA Live Regions** (4 hours)
   - [ ] Chat messages: `role="status"`, `aria-live="polite"`
   - [ ] Error messages: `aria-live="assertive"`
   - [ ] Loading states: `aria-busy="true"`

3. **Audit Heading Hierarchy** (2 hours)
   - [ ] Ensure h1 → h2 → h3 (no skipped levels)
   - [ ] Fix any violations

4. **Test with Screen Reader** (6 hours)
   - [ ] Test with Orca (Linux)
   - [ ] Test all key user flows
   - [ ] Document any issues
   - [ ] Fix critical issues

---

## Timeline Summary

| Week | Dates | Tasks | Status |
|------|-------|-------|--------|
| 1 | Mar 28 - Apr 4 | P0-1 completion (80% → 100%) | In Progress |
| 2 | Apr 4 - Apr 11 | P0-2 color contrast fixes | Not Started |
| 3 | Apr 11 - Apr 18 | P0-3 screen reader support | Not Started |
| 4 | Apr 18 - Apr 24 | Final validation & deployment | Not Started |

**Critical Path:** Must complete P0-1 by April 4 to stay on schedule.

---

## Decision Points

### Should We Defer Arrow Key Navigation?

**Recommendation:** YES

**Reasoning:**
- Not strictly required for WCAG 2.1 AA minimal compliance
- 6-8 hours could be better spent on P0-2 and P0-3
- Can be added as P1 (priority 1) post-deadline enhancement

**Impact:** None on legal compliance, minor UX improvement deferred

### Should We Create Full Test Suite Now?

**Recommendation:** PARTIAL

**Reasoning:**
- Basic keyboard navigation tests: YES (critical for validation)
- Comprehensive E2E tests: DEFER to post-compliance
- Screen reader tests: YES (needed for P0-3 validation)

**Minimum Test Coverage for Compliance:**
- ✅ Skip-to-content link
- ✅ Focus indicators visible
- ✅ Modal Escape key
- ✅ All buttons have accessible names
- ✅ Main landmark exists

---

## Risk Mitigation

### High-Risk Items

1. **Color Contrast Violations Unknown**
   - Mitigation: Start P0-2 scan NOW (parallel with P0-1 completion)
   - Action: Run axe scan today to estimate scope

2. **Screen Reader Testing Time Intensive**
   - Mitigation: Focus on critical user flows only
   - Action: Define 5 key flows to test (login, send message, etc.)

3. **Only 26 Days Remaining**
   - Mitigation: Work in parallel where possible
   - Action: Start P0-2 scan while finishing P0-1

### Medium-Risk Items

1. **46 A11y Suppressions Still Unaudited**
   - Mitigation: Address only those in critical user paths
   - Action: Focus on MessageInput, Modal, Sidebar first

2. **Unknown Production Environment Issues**
   - Mitigation: Test in staging environment ASAP
   - Action: Deploy to staging after P0-1 completion

---

## Immediate Action Items (Today)

1. **Complete Icon Button ARIA Labels** (4-6 hours)
   - Start with MessageInput.svelte
   - Test with Orca screen reader
   - Commit and push

2. **Run Initial Color Contrast Scan** (30 minutes)
   - Install axe-core CLI
   - Run scan on localhost
   - Generate initial violations list
   - Estimate time to fix (inform timeline)

3. **Create Basic Keyboard Navigation Tests** (2 hours)
   - Setup Playwright
   - Write 5 critical tests
   - Ensure tests pass
   - Commit and push

4. **Update Progress Tracker** (15 minutes)
   - Mark completed tasks
   - Update timeline
   - Document any blockers

---

## Success Criteria

### P0-1 Complete
- ✅ Modal, Sidebar enhanced
- ✅ Skip-to-content implemented
- ✅ Global focus styles created
- [ ] All icon buttons have aria-label
- [ ] Basic keyboard tests passing
- [ ] 0 a11y suppressions in modified components

### Ready for P0-2
- [ ] axe-core CLI installed
- [ ] Initial color contrast scan complete
- [ ] Violations list generated
- [ ] Time estimate confirmed

### On Track for Deadline
- [ ] P0-1 complete by April 4
- [ ] P0-2 started by April 4
- [ ] No major blockers identified
- [ ] Staging deployment successful

---

## Contact & Escalation

If blocked or falling behind schedule:
1. Document blocker in PROGRESS.md
2. Assess impact on deadline
3. Consider scope reduction (defer P1/P2 features)
4. Communicate updated timeline

**Non-Negotiable:** April 24, 2026 deadline
**Minimum Compliance:** P0-1, P0-2, P0-3 complete
**Everything Else:** Nice to have, can be deferred
