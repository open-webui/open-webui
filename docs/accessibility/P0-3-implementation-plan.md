# P0-3 Screen Reader Support - Implementation Plan

**Document Version:** 1.0
**Created:** March 28, 2026
**Target Start:** April 11, 2026
**Target Completion:** April 18, 2026
**Total Estimated Time:** 17-22 hours (over 7 days = ~3 hours/day)
**Owner:** Development Agent

---

## Overview

This implementation plan provides step-by-step instructions for adding comprehensive screen reader support to Open-WebUI to achieve WCAG 2.1 Level AA compliance.

### Scope
- Fix 69 images without alt text
- Add ARIA live regions for dynamic content
- Associate all form inputs with labels
- Fix heading hierarchy
- Improve link text quality
- Add dynamic page titles
- Add state communication (aria-expanded, aria-busy, etc.)

### Out of Scope (P1/P2)
- Advanced ARIA patterns (grid, tree, etc.)
- Custom keyboard shortcuts beyond Tab/Enter/Escape
- AAA-level enhancements

---

## Task Breakdown

### Task 1: Add Alt Text to All Images (4-5 hours)

**Priority:** P0 - CRITICAL
**Dependencies:** None
**Complexity:** Low (repetitive but straightforward)

#### 1.1 Logo and Branding Images (30 minutes)

**Files to Modify:**
- `src/lib/components/app/AppSidebar.svelte`
- `src/app.html`

**AppSidebar.svelte Changes:**

**Location 1:** Main logo (around line 80-85)
```svelte
<!-- BEFORE -->
<img
    src="{WEBUI_BASE_URL}/static/splash.png"
    class="size-11 dark:invert p-0.5"
/>

<!-- AFTER -->
<img
    src="{WEBUI_BASE_URL}/static/splash.png"
    alt="Open WebUI Logo"
    class="size-11 dark:invert p-0.5"
/>
```

**Location 2:** Favicon (around line 90-95)
```svelte
<!-- BEFORE -->
<img
    src="{WEBUI_BASE_URL}/static/favicon.png"
    class="size-10 {selected === '' ? 'rounded-2xl' : 'rounded-full'}"
/>

<!-- AFTER -->
<img
    src="{WEBUI_BASE_URL}/static/favicon.png"
    alt="Open WebUI"
    class="size-10 {selected === '' ? 'rounded-2xl' : 'rounded-full'}"
/>
```

**app.html Changes:**

**Location:** Splash screen logos (lines 89-102, 138-143)
```html
<!-- BEFORE (line ~92) -->
<img
    id="logo"
    style="position: absolute; width: auto; height: 6rem; ..."
    src={isDarkMode ? '/static/splash-dark.png' : '/static/splash.png'}
/>

<!-- AFTER -->
<img
    id="logo"
    alt="Open WebUI"
    style="position: absolute; width: auto; height: 6rem; ..."
    src={isDarkMode ? '/static/splash-dark.png' : '/static/splash.png'}
/>

<!-- BEFORE (line ~139) -->
<img
    id="logo-her"
    style="width: auto; height: 13rem"
    src="/static/splash.png"
    class="animate-pulse-fast"
/>

<!-- AFTER -->
<img
    id="logo-her"
    alt="Open WebUI Loading"
    style="width: auto; height: 13rem"
    src="/static/splash.png"
    class="animate-pulse-fast"
/>
```

---

#### 1.2 User Profile/Avatar Images (1-1.5 hours)

**Pattern:** Profile images should have alt text describing the user

**Files to Modify:**
- `src/lib/components/admin/Users/UserList.svelte`
- `src/lib/components/admin/Evaluations/Feedbacks.svelte`
- `src/lib/components/admin/Evaluations/Leaderboard.svelte`
- `src/lib/components/channel/ChannelInfoModal/UserList.svelte`
- `src/lib/components/channel/MessageInput/MentionList.svelte`
- `src/lib/components/channel/Messages.svelte`
- `src/lib/components/channel/Messages/Message.svelte`

**Generic Pattern:**
```svelte
<!-- BEFORE -->
<img
    src={user.profile_image_url}
    class="rounded-full size-8"
/>

<!-- AFTER -->
<img
    src={user.profile_image_url}
    alt="{user.name}'s profile picture"
    class="rounded-full size-8"
/>

<!-- If user.name might be undefined, use fallback -->
<img
    src={user.profile_image_url}
    alt="{user.name || 'User'}'s profile picture"
    class="rounded-full size-8"
/>
```

**Special Cases:**

If the image is purely decorative next to visible name text:
```svelte
<!-- User name is visible right next to image -->
<img src={user.avatar} alt="" role="presentation" />
<span>{user.name}</span>
```

---

#### 1.3 Model and Provider Icons (1-1.5 hours)

**Files to Modify:**
- `src/lib/components/admin/Settings/Models.svelte`
- `src/lib/components/admin/Settings/Evaluations/Model.svelte`
- `src/lib/components/admin/Settings/Evaluations/ArenaModelModal.svelte`
- `src/lib/components/admin/Analytics/Dashboard.svelte`
- `src/lib/components/admin/Analytics/ModelUsage.svelte`

**Pattern:**
```svelte
<!-- BEFORE -->
<img
    src={model.info?.meta?.profile_image_url}
    class="size-8 rounded-lg"
/>

<!-- AFTER -->
<img
    src={model.info?.meta?.profile_image_url}
    alt="{model.name || 'Model'} logo"
    class="size-8 rounded-lg"
/>
```

---

#### 1.4 General Settings Images (30 minutes)

**Files to Modify:**
- `src/lib/components/admin/Settings/General.svelte` (3 images)

**Pattern:** Check each image context:
- If functional (clickable, conveys info): descriptive alt
- If decorative: `alt=""` or `role="presentation"`

---

#### 1.5 Batch Update Remaining Images (1 hour)

**Process:**
1. Generate list of all remaining images:
   ```bash
   grep -rn "<img" src/lib/components/ | grep -v "alt=" > /tmp/images-no-alt.txt
   ```

2. For each image, determine:
   - **Functional:** Descriptive alt text
   - **Decorative:** `alt=""` OR `role="presentation"`

3. Apply fixes systematically

---

**Validation for Task 1:**
```bash
# Should return 0 after fixes
grep -r "<img" src/lib/components/ | grep -v "alt=" | wc -l

# Check app.html separately
grep "<img" src/app.html | grep -v "alt="
```

**Testing:**
- Start Orca screen reader
- Navigate to pages with images
- Verify screen reader announces appropriate alt text
- Decorative images should be skipped

---

### Task 2: Add ARIA Live Regions (4-5 hours)

**Priority:** P0 - CRITICAL
**Dependencies:** None
**Complexity:** Medium (requires understanding of state updates)

#### 2.1 Fix NotificationToast (15 minutes)

**File:** `src/lib/components/NotificationToast.svelte`

**Current (line ~86):**
```svelte
<div role="status">
    <!-- Toast content -->
</div>
```

**Fixed:**
```svelte
<div
    role="status"
    aria-live="polite"
    aria-atomic="true"
>
    <!-- Toast content -->
</div>
```

---

#### 2.2 Add Error Message Live Region (1 hour)

**Goal:** Announce form validation and API errors

**Pattern for Form Errors:**
```svelte
<label for="email">Email Address</label>
<input
    id="email"
    type="email"
    bind:value={email}
    aria-invalid={emailError ? 'true' : 'false'}
    aria-describedby={emailError ? 'email-error' : undefined}
/>
{#if emailError}
<span
    id="email-error"
    role="alert"
    aria-live="assertive"
    class="error-text"
>
    {emailError}
</span>
{/if}
```

**Files to Audit for Form Errors:**
- All forms in `src/lib/components/admin/Settings/`
- Login/signup forms
- Model configuration forms
- Any user input validation

**Implementation Strategy:**
1. Find all form error messages
2. Wrap in `<span role="alert" aria-live="assertive">`
3. Associate with input via `aria-describedby`
4. Set `aria-invalid="true"` on invalid inputs

---

#### 2.3 Add Loading State Live Regions (1.5 hours)

**Goal:** Announce loading states to screen readers

**Pattern 1: Loading Spinner with Context**
```svelte
{#if isLoading}
<div
    aria-busy="true"
    aria-live="polite"
    aria-label="Loading {loadingContext}"
>
    <Spinner />
    <span class="sr-only">Loading {loadingContext}</span>
</div>
{/if}
```

**Pattern 2: Button with Loading State**
```svelte
<button
    aria-busy={isLoading}
    disabled={isLoading}
>
    {#if isLoading}
        <Spinner class="inline" />
        <span class="sr-only">Loading...</span>
    {:else}
        Send Message
    {/if}
</button>
```

**Locations:**
- Chat message generation: "Loading response"
- File upload: "Uploading file"
- Model loading: "Loading model"
- Settings save: "Saving settings"

---

#### 2.4 Add Status Announcement Live Region (1-1.5 hours)

**Goal:** Announce successful actions

**Pattern: Hidden Status Announcer**
```svelte
<script>
  let statusMessage = '';
  let statusKey = 0; // Force re-render

  function announceStatus(message: string) {
    statusMessage = message;
    statusKey += 1;
    // Clear after announcement
    setTimeout(() => {
      statusMessage = '';
    }, 3000);
  }

  // Example usage
  async function saveSettings() {
    await api.saveSettings();
    announceStatus('Settings saved successfully');
  }
</script>

{#key statusKey}
  {#if statusMessage}
  <div
    role="status"
    aria-live="polite"
    class="sr-only"
  >
    {statusMessage}
  </div>
  {/if}
{/key}
```

**Locations:**
- Message sent successfully
- File uploaded successfully
- Settings saved
- Model switched
- Chat history updated

---

#### 2.5 Verify Chat Messages Live Region (15 minutes)

**File:** `src/lib/components/chat/Messages.svelte` (line 467)

**Current Implementation:**
```svelte
<ul
    role="log"
    aria-live="polite"
    aria-relevant="additions"
    aria-atomic="false"
>
    <!-- Messages -->
</ul>
```

**Status:** ✅ **Already correct** - just verify in testing

**Additional Consideration:**
Each message should have clear role:
```svelte
{#each messages as message}
<li role="article" aria-label="{message.role} message">
    {@html message.content}
</li>
{/each}
```

---

**Validation for Task 2:**
```bash
# Count live regions
grep -rn "aria-live" src/lib/components/ | wc -l
# Should be significantly higher than 3

# Check for role="alert" (errors)
grep -rn "role=\"alert\"" src/lib/components/ | wc -l
# Should have at least 5-10 instances

# Check for aria-busy
grep -rn "aria-busy" src/lib/components/ | wc -l
# Should have at least 5-10 instances
```

**Testing:**
- Start Orca screen reader
- Perform actions that trigger loading, errors, status messages
- Verify announcements are made
- Verify timing is appropriate (not too fast, not too slow)

---

### Task 3: Associate Form Labels (3-4 hours)

**Priority:** P0 - CRITICAL
**Dependencies:** None
**Complexity:** Medium (many scattered inputs)

#### 3.1 Audit All Form Inputs (1 hour)

**Process:**
```bash
# Find all input elements
grep -rn "<input\|<textarea\|<select" src/lib/components/ > /tmp/all-inputs.txt

# Check which have labels
grep -rn "<input\|<textarea\|<select" src/lib/components/ | \
  grep -E "aria-label|aria-labelledby|id=" | \
  wc -l
```

**Create Spreadsheet:**
- File path
- Line number
- Input type
- Has label? (yes/no)
- Label type (label element, aria-label, aria-labelledby, none)

#### 3.2 Add Labels to Unlabeled Inputs (2-3 hours)

**Pattern 1: Visible Label**
```svelte
<label for="model-temperature">
    Model Temperature
    <span class="text-gray-500 text-xs">(0-1)</span>
</label>
<input
    id="model-temperature"
    type="number"
    bind:value={temperature}
    min="0"
    max="1"
    step="0.1"
/>
```

**Pattern 2: ARIA Label (for compact UIs)**
```svelte
<input
    type="text"
    aria-label="Search chats"
    placeholder="Search..."
    bind:value={searchQuery}
/>
```

**Pattern 3: Wrapping Label**
```svelte
<label class="flex items-center gap-2">
    <input type="checkbox" bind:checked={enabled} />
    <span>Enable feature</span>
</label>
```

**Pattern 4: Label by ID Reference**
```svelte
<div id="temperature-label">Temperature</div>
<input
    type="range"
    aria-labelledby="temperature-label"
    bind:value={temperature}
/>
```

---

**High-Priority Files:**
- `src/lib/components/chat/MessageInput.svelte` (line 1126 and others)
- All settings forms
- All admin forms
- Login/signup forms

---

**Validation for Task 3:**
```bash
# After fixes, this should be much smaller
grep -rn "<input\|<textarea\|<select" src/lib/components/ | \
  grep -v "aria-label" | \
  grep -v "aria-labelledby" | \
  wc -l
```

**Testing:**
- Navigate to each form with screen reader
- Tab through all inputs
- Verify each input announces its purpose
- Check for "edit text, unlabeled" (failure case)

---

### Task 4: Fix Heading Hierarchy (2-3 hours)

**Priority:** P0 - CRITICAL
**Dependencies:** None
**Complexity:** Medium (requires understanding of page structure)

#### 4.1 Add H1 to Main Pages (1 hour)

**Files to Check:**
- `src/routes/(app)/+page.svelte` - Main chat page
- `src/routes/(app)/admin/+page.svelte` - Admin dashboard
- Other top-level pages

**Pattern:**
```svelte
<!-- Main chat page -->
<h1 class="sr-only">Chat</h1>

<!-- Or visible -->
<h1 class="text-2xl font-bold mb-4">
    {$WEBUI_NAME}
</h1>
```

**Note:** H1 can be visually hidden with `.sr-only` if design doesn't require visible page title

---

#### 4.2 Fix Modal Heading Levels (1 hour)

**Files to Modify:**
- `src/lib/components/chat/MessageInput/AttachWebpageModal.svelte:40`
- `src/lib/components/chat/Settings/Interface/ManageFloatingActionButtonsModal.svelte:33`
- `src/lib/components/chat/Settings/Interface/ManageImageCompressionModal.svelte:29`

**Pattern:**
```svelte
<!-- BEFORE -->
<h1 class="text-lg font-medium self-center font-primary">
    Modal Title
</h1>

<!-- AFTER -->
<h2 class="text-lg font-medium self-center font-primary">
    Modal Title
</h2>
```

**Rationale:** Modals are dialogs, not new pages, so should use h2 or h3

---

#### 4.3 Audit Section Headings (1 hour)

**Goal:** Ensure no heading level skips

**Process:**
1. Extract all heading usage:
   ```bash
   grep -rn "<h[1-6]" src/lib/components/ > /tmp/headings.txt
   ```

2. For each file, verify hierarchy:
   - Page has one h1
   - Sections use h2
   - Subsections use h3
   - No h1 → h3 skips

3. Fix violations

**Example Structure:**
```svelte
<h1>Settings</h1>

<section>
    <h2>Account</h2>
    <div>
        <h3>Profile</h3>
        <!-- Profile settings -->
    </div>
    <div>
        <h3>Security</h3>
        <!-- Security settings -->
    </div>
</section>

<section>
    <h2>Appearance</h2>
    <!-- Appearance settings -->
</section>
```

---

**Validation for Task 4:**

**Automated Check:**
```javascript
// Playwright test
test('heading hierarchy is correct', async ({ page }) => {
    await page.goto('/');

    const headings = await page.locator('h1, h2, h3, h4, h5, h6').allTextContents();
    const levels = await page.locator('h1, h2, h3, h4, h5, h6').evaluateAll(elements =>
        elements.map(el => parseInt(el.tagName[1]))
    );

    // Check for single h1
    const h1Count = levels.filter(l => l === 1).length;
    expect(h1Count).toBe(1);

    // Check for no skipped levels
    for (let i = 1; i < levels.length; i++) {
        const diff = levels[i] - levels[i-1];
        expect(diff).toBeLessThanOrEqual(1);
    }
});
```

**Manual Testing:**
- Use browser extension "HeadingsMap"
- Navigate through site
- Verify logical structure
- Test with screen reader heading navigation (H key in Orca)

---

### Task 5: Improve Link Text Quality (1-2 hours)

**Priority:** P1 - IMPORTANT
**Dependencies:** None
**Complexity:** Low

#### 5.1 Replace "click here" Links

**Files to Modify:**
- `src/lib/components/admin/Settings/Models/Manage/ManageOllama.svelte:713`
- `src/lib/components/admin/Settings/Models/Manage/ManageOllama.svelte:1092`
- `src/lib/components/admin/Settings/Audio.svelte:492, 639, 649`

**Pattern:**
```svelte
<!-- BEFORE -->
To configure models, <a href="/docs/models">click here</a>.

<!-- AFTER -->
<a href="/docs/models">Configure models in the documentation</a>.

<!-- OR -->
To configure models, view the
<a href="/docs/models">model configuration guide</a>.
```

#### 5.2 Make "learn more" Links Descriptive

**Pattern:**
```svelte
<!-- BEFORE -->
<a href="/docs/audio">Learn more</a> about audio settings.

<!-- AFTER -->
<a href="/docs/audio">Learn more about audio settings</a>.
```

---

**Validation:**
```bash
# Should return 0 after fixes
grep -rn "click here\|>here<" src/lib/components/ | wc -l
```

**Testing:**
- Navigate with screen reader
- Verify link announcements are clear
- Test out-of-context (screen readers can list all links)

---

### Task 6: Add Dynamic Page Titles (1 hour)

**Priority:** P1 - IMPORTANT
**Dependencies:** None
**Complexity:** Low

#### 6.1 Implement Dynamic Titles

**File:** `src/routes/+layout.svelte`

**Add After Imports:**
```svelte
<script>
  import { page } from '$app/stores';
  import { chatId, chats, WEBUI_NAME } from '$lib/stores';

  $: pageTitle = (() => {
    const routeId = $page.route.id || '';

    // Admin pages
    if (routeId.includes('/admin/settings')) {
      return `Settings - ${$WEBUI_NAME}`;
    }
    if (routeId.includes('/admin/analytics')) {
      return `Analytics - ${$WEBUI_NAME}`;
    }
    if (routeId.includes('/admin')) {
      return `Admin Dashboard - ${$WEBUI_NAME}`;
    }

    // Workspace pages
    if (routeId.includes('/workspace')) {
      return `Workspace - ${$WEBUI_NAME}`;
    }

    // Specific chat
    if ($chatId && $chats?.[$chatId]?.title) {
      return `${$chats[$chatId].title} - ${$WEBUI_NAME}`;
    }

    // Default: Chat
    return `Chat - ${$WEBUI_NAME}`;
  })();
</script>

<svelte:head>
  <title>{pageTitle}</title>
</svelte:head>
```

**Position:** Add just after `<script>` section, before `{@html ...}` or `<slot />`

---

**Validation:**
- Navigate between pages
- Check browser tab title updates
- Verify pattern: "[Page] - Open WebUI"

---

### Task 7: Add State Communication Attributes (2-3 hours)

**Priority:** P1 - IMPORTANT
**Dependencies:** None
**Complexity:** Medium

#### 7.1 Add aria-expanded to Collapsible Sections

**Pattern:**
```svelte
<script>
  let isExpanded = false;
</script>

<button
    aria-expanded={isExpanded}
    aria-controls="section-content"
    on:click={() => isExpanded = !isExpanded}
>
    {isExpanded ? 'Collapse' : 'Expand'} Section
    <ChevronIcon class={isExpanded ? 'rotate-90' : ''} />
</button>

<div id="section-content" hidden={!isExpanded}>
    <!-- Content -->
</div>
```

**Locations:**
- Settings panels with collapsible sections
- Sidebar folders
- Any expandable UI elements

---

#### 7.2 Add aria-selected to Selectable Items

**Pattern:**
```svelte
<div
    role="option"
    aria-selected={selectedModelId === model.id}
    tabindex={selectedModelId === model.id ? 0 : -1}
    on:click={() => selectModel(model.id)}
>
    {model.name}
</div>
```

**Locations:**
- Model selector
- Chat history items
- Any selectable list

---

#### 7.3 Enhance Existing aria-pressed Buttons

**File:** `src/lib/components/chat/MessageInput.svelte`

**Current (lines 1714, 1734, 1756):**
```svelte
<button aria-pressed={webSearchEnabled}>
```

**Enhancement (ensure aria-label also describes state):**
```svelte
<button
    aria-label="Web search: {webSearchEnabled ? 'enabled' : 'disabled'}"
    aria-pressed={webSearchEnabled}
>
    <SearchIcon />
</button>
```

**Note:** This makes the state redundant in the label since `aria-pressed` already communicates it. Consider removing state from label:
```svelte
<button
    aria-label="Toggle web search"
    aria-pressed={webSearchEnabled}
>
    <SearchIcon />
</button>
```

---

**Validation:**
```bash
# Check for aria-expanded usage
grep -rn "aria-expanded" src/lib/components/ | wc -l
# Should have at least 5-10 instances

# Check for aria-selected usage
grep -rn "aria-selected" src/lib/components/ | wc -l
# Should have at least 3-5 instances
```

**Testing:**
- Expand/collapse sections with screen reader
- Verify "expanded" and "collapsed" announcements
- Select items and verify "selected" announcement
- Test toggle buttons and verify state changes announced

---

### Task 8: Add Semantic Landmarks (1-2 hours)

**Priority:** P2 - ENHANCEMENT
**Dependencies:** Understanding of layout structure
**Complexity:** Low

#### 8.1 Identify Navbar Component

**Search for header/top navigation:**
```bash
grep -rn "navbar\|header\|top-nav" src/lib/components/layout/
```

**If found, wrap in:**
```svelte
<header role="banner" aria-label="Site header">
    <!-- Navbar content -->
</header>
```

---

#### 8.2 Wrap Sidebar in Nav

**File:** `src/lib/components/layout/Sidebar.svelte`

**Current Structure:**
```svelte
<aside role="complementary" aria-label="Chat history and navigation">
    <!-- Sidebar content -->
</aside>
```

**Consider adding:**
```svelte
<aside role="complementary" aria-label="Chat history and navigation">
    <nav role="navigation" aria-label="Main navigation">
        <!-- Navigation items (New Chat, folders, etc.) -->
    </nav>

    <section aria-label="Chat history">
        <!-- Chat list -->
    </section>
</aside>
```

---

#### 8.3 Add Footer (if applicable)

**Check if footer exists:**
```bash
grep -rn "footer" src/lib/components/layout/
```

**If found:**
```svelte
<footer role="contentinfo" aria-label="Site footer">
    <!-- Footer content -->
</footer>
```

---

**Validation:**
```bash
grep -rn "role=\"banner\"\|role=\"navigation\"\|role=\"contentinfo\"" src/lib/components/ | wc -l
# Should have at least 2-3 instances
```

**Testing:**
- Use screen reader landmark navigation (D key in Orca)
- Verify banner, navigation, main, complementary landmarks
- Ensure logical order and clear labels

---

## Testing Checklist

### Automated Tests

#### Create `tests/accessibility/screen-reader.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Screen Reader Support - P0-3', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('http://localhost:3000');
    });

    test('all images have alt attributes', async ({ page }) => {
        const imagesWithoutAlt = await page.locator('img:not([alt])').count();
        expect(imagesWithoutAlt).toBe(0);
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

    test('page has exactly one h1', async ({ page }) => {
        const h1Count = await page.locator('h1').count();
        expect(h1Count).toBe(1);
    });

    test('heading hierarchy has no skipped levels', async ({ page }) => {
        const levels = await page.locator('h1, h2, h3, h4, h5, h6').evaluateAll(elements =>
            elements.map(el => parseInt(el.tagName[1]))
        );

        for (let i = 1; i < levels.length; i++) {
            const diff = levels[i] - levels[i - 1];
            expect(diff).toBeLessThanOrEqual(1);
        }
    });

    test('all form inputs have labels', async ({ page }) => {
        const inputs = await page.locator('input:visible, textarea:visible, select:visible').all();

        for (const input of inputs) {
            const id = await input.getAttribute('id');
            const ariaLabel = await input.getAttribute('aria-label');
            const ariaLabelledBy = await input.getAttribute('aria-labelledby');

            let hasLabel = ariaLabel || ariaLabelledBy;

            if (!hasLabel && id) {
                const label = page.locator(`label[for="${id}"]`);
                hasLabel = (await label.count()) > 0;
            }

            if (!hasLabel) {
                const html = await input.evaluate(el => el.outerHTML);
                console.error('Input without label:', html);
            }

            expect(hasLabel).toBeTruthy();
        }
    });

    test('ARIA live regions exist', async ({ page }) => {
        // Check for at least one live region
        const liveRegions = await page.locator('[aria-live]').count();
        expect(liveRegions).toBeGreaterThan(0);
    });

    test('no generic link text', async ({ page }) => {
        const badLinkText = await page.locator('a:has-text("click here"), a:has-text("here")').count();
        expect(badLinkText).toBe(0);
    });

    test('page title is descriptive', async ({ page }) => {
        const title = await page.title();
        expect(title).toContain('Open WebUI');
        expect(title.length).toBeGreaterThan(10);
    });
});
```

#### Run Tests
```bash
npx playwright test tests/accessibility/screen-reader.spec.ts --headed
```

---

### Manual Testing with Orca

#### Setup
```bash
# Install Orca if not already installed
sudo dnf install orca

# Start Orca
orca --enable=speech
```

#### Test Scenarios

**Scenario 1: Navigate Entire App**
- Start Orca
- Open Open-WebUI in Firefox
- Navigate through app using Tab only
- Verify all elements are announced
- Check for "unlabeled" announcements (failures)

**Scenario 2: Send Chat Message**
- Navigate to message input
- Type message
- Press Send button
- Verify message appears in chat
- Verify new message is announced via live region

**Scenario 3: Select Model**
- Navigate to model selector
- Open dropdown
- Verify all models are announced
- Select different model
- Verify selection is announced

**Scenario 4: Form Validation**
- Navigate to settings
- Enter invalid data
- Submit form
- Verify error message is announced immediately
- Verify error is associated with input field

**Scenario 5: Heading Navigation**
- Press H key to navigate by headings
- Verify logical structure
- Verify no "heading level 1" → "heading level 3" skips

**Scenario 6: Landmark Navigation**
- Press D key to navigate by landmarks
- Verify banner, navigation, main, complementary landmarks
- Verify logical order

**Scenario 7: Image Descriptions**
- Navigate to areas with images
- Verify all functional images have descriptions
- Verify decorative images are skipped

---

### Success Criteria

P0-3 is COMPLETE when all of these pass:

- [ ] All 69 images have `alt` attribute or `role="presentation"`
- [ ] No "unlabeled image" announcements in screen reader
- [ ] All buttons have accessible names
- [ ] No "unlabeled button" announcements
- [ ] All form inputs have associated labels
- [ ] No "unlabeled edit text" announcements
- [ ] ARIA live regions announce:
  - [ ] New chat messages
  - [ ] Form errors (immediately)
  - [ ] Status messages (after actions)
  - [ ] Loading states
- [ ] Heading hierarchy:
  - [ ] Each page has exactly one h1
  - [ ] No skipped levels (h1 → h3)
  - [ ] Logical structure (H key navigation works)
- [ ] Page titles:
  - [ ] Dynamic based on current view
  - [ ] Descriptive and meaningful
- [ ] Link text:
  - [ ] No "click here" or "here" generic text
  - [ ] Purpose clear from link text alone
- [ ] State communication:
  - [ ] Toggle buttons use `aria-pressed`
  - [ ] Expandable sections use `aria-expanded`
  - [ ] Selectable items use `aria-selected`
  - [ ] Loading states use `aria-busy`
- [ ] Automated tests:
  - [ ] All screen reader tests pass
  - [ ] axe-core scan: 0 ARIA violations
- [ ] Manual tests:
  - [ ] All 7 Orca test scenarios pass
  - [ ] No unexpected "unlabeled" announcements
  - [ ] All key user flows work with screen reader

---

## Risk Mitigation

### Risk 1: Large Scope (69 Images)
**Mitigation:**
- Use batch find/replace where possible
- Create script to generate image list with context
- Work in priority order (user-facing first)

### Risk 2: Complex State Management
**Mitigation:**
- Start with simple cases (NotificationToast)
- Study existing implementation (Messages.svelte)
- Test incrementally after each addition

### Risk 3: Form Label Associations
**Mitigation:**
- Create comprehensive audit spreadsheet
- Use consistent patterns
- Validate with automated tests

### Risk 4: Breaking Visual Design
**Mitigation:**
- Use `.sr-only` class for screen-reader-only content
- Test visual appearance after each change
- Consult with designer if major changes needed

---

## Timeline

**Total: 17-22 hours over 7 days**

### Day 1 (April 11) - 3 hours
- Task 1.1-1.2: Logo, branding, avatar images (2 hours)
- Task 2.1: Fix NotificationToast (15 minutes)
- Task 2.2: Start error message live regions (45 minutes)

### Day 2 (April 12) - 3 hours
- Task 1.3-1.4: Model icons, settings images (2 hours)
- Task 2.2: Complete error message live regions (1 hour)

### Day 3 (April 13) - 3 hours
- Task 1.5: Batch update remaining images (1 hour)
- Task 2.3: Loading state live regions (1.5 hours)
- Task 2.4: Start status announcements (30 minutes)

### Day 4 (April 14) - 3 hours
- Task 2.4: Complete status announcements (1 hour)
- Task 2.5: Verify chat messages live region (15 minutes)
- Task 3.1: Audit all form inputs (1 hour)
- Task 3.2: Start adding form labels (45 minutes)

### Day 5 (April 15) - 3 hours
- Task 3.2: Complete form labels (2 hours)
- Task 4.1: Add h1 to main pages (1 hour)

### Day 6 (April 16) - 3 hours
- Task 4.2: Fix modal heading levels (1 hour)
- Task 4.3: Audit section headings (1 hour)
- Task 5: Improve link text quality (1 hour)

### Day 7 (April 17) - 3 hours
- Task 6: Add dynamic page titles (1 hour)
- Task 7: Add state communication attributes (2 hours)

### Day 8 (April 18) - Buffer Day
- Write automated tests
- Run manual Orca testing
- Fix any issues found
- Validate all success criteria

---

## Deployment Checklist

Before declaring P0-3 complete:

- [ ] All tasks completed
- [ ] All automated tests passing
- [ ] All manual tests passing
- [ ] axe-core scan: 0 ARIA violations
- [ ] Code reviewed
- [ ] Committed to feature branch
- [ ] PR created with full description
- [ ] Deployed to staging
- [ ] Validated in staging with Orca
- [ ] Approved for production

---

## References

- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Orca Screen Reader User Guide](https://help.gnome.org/users/orca/stable/)
- [WebAIM: ARIA Live Regions](https://webaim.org/techniques/aria/#liveregions)
- [MDN: ARIA](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA)

---

**Implementation Plan Complete:** March 28, 2026
**Ready for Development Agent Handoff**
