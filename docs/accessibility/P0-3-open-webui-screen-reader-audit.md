# Open-WebUI Screen Reader Accessibility Audit

**Audit Date:** March 28, 2026
**Auditor:** UI/UX Research Agent
**Tool Set:** grep, code analysis, WCAG 2.1 Level AA criteria
**Deadline:** April 24, 2026 (27 days remaining)

---

## Executive Summary

This audit identifies screen reader accessibility violations in Open-WebUI against WCAG 2.1 Level A and AA success criteria. The audit covers image alt text, ARIA attributes, semantic HTML, form labels, heading hierarchy, and live regions.

### Critical Statistics

- **Images without alt text:** 69 instances
- **Existing ARIA live regions:** 3 (partial coverage)
- **Semantic landmark elements:** 1 (`<main>` only)
- **ARIA banner/navigation/contentinfo roles:** 0
- **Heading hierarchy issues:** Multiple (requires detailed analysis)
- **Forms without labels:** Multiple (requires component-level audit)
- **Poor link text instances:** 8+ occurrences ("click here", "learn more")
- **Existing ARIA pressed states:** 3 (web search, image gen, code interpreter toggles)

### Priority Classification

| Priority | Violations | Estimated Fix Time |
|----------|-----------|-------------------|
| **P0 (Critical)** | 69 images, missing live regions, form labels | 12-15 hours |
| **P1 (Important)** | Link text quality, heading hierarchy | 3-4 hours |
| **P2 (Nice to have)** | Consistent identification, enhanced instructions | 2-3 hours |

**Total Estimated Effort:** 17-22 hours

---

## 1. Non-text Content Violations (WCAG 1.1.1 - Level A)

### 1.1 Images Without Alt Text

**Violation Count:** 69 instances across components

**Critical Instances:**

#### AppSidebar.svelte
```svelte
<!-- Line ~80-85 -->
<img
    src="{WEBUI_BASE_URL}/static/splash.png"
    class="size-11 dark:invert p-0.5"
/>
<!-- MISSING: alt="Open WebUI Logo" -->

<!-- Line ~90-95 -->
<img
    src="{WEBUI_BASE_URL}/static/favicon.png"
    class="size-10 {selected === '' ? 'rounded-2xl' : 'rounded-full'}"
/>
<!-- MISSING: alt="Open WebUI" or alt="" (if decorative) -->
```

#### Avatar/Profile Images (Multiple Components)
**Locations:**
- `src/lib/components/admin/Evaluations/Feedbacks.svelte`
- `src/lib/components/admin/Users/UserList.svelte`
- `src/lib/components/channel/Messages/Message.svelte`
- `src/lib/components/chat/Messages/Message.svelte` (likely similar structure)

**Pattern:**
```svelte
<img
    src={user.profile_image_url}
    class="rounded-full size-8"
/>
<!-- MISSING: alt="{user.name}'s profile picture" -->
```

**Expected Fix:**
```svelte
<img
    src={user.profile_image_url}
    alt="{user.name}'s profile picture"
    class="rounded-full size-8"
/>
```

#### Model/AI Provider Icons
**Locations:**
- `src/lib/components/admin/Settings/Models.svelte`
- `src/lib/components/admin/Settings/Evaluations/Model.svelte`
- `src/lib/components/admin/Settings/Evaluations/ArenaModelModal.svelte`

**Pattern:**
```svelte
<img
    src={model.info?.meta?.profile_image_url}
    class="size-8"
/>
<!-- MISSING: alt="{model.name} logo" -->
```

#### Splash/Loading Images
**Location:** `src/app.html` (lines 89-102)
```html
<img
    id="logo"
    style="position: absolute; width: auto; height: 6rem; ..."
    src={isDarkMode ? '/static/splash-dark.png' : '/static/splash.png'}
/>
<!-- MISSING: alt="Open WebUI" -->

<img
    id="logo-her"
    style="width: auto; height: 13rem"
    src="/static/splash.png"
    class="animate-pulse-fast"
/>
<!-- MISSING: alt="Open WebUI Loading" -->
```

### 1.2 Icon-Only Elements

**Status:** ✅ **MOSTLY COMPLETE** from P0-1
- MessageInput.svelte: 17 icon buttons now have aria-labels (completed March 28)
- Sidebar.svelte: Icon buttons verified to have labels

**Remaining Issues:**
- Some admin panel icon buttons may still need labels
- Model selector dropdown icons
- Settings panel icons

---

## 2. Info and Relationships (WCAG 1.3.1 - Level A)

### 2.1 Semantic HTML - Landmarks

**Current State:**
- ✅ `<main>` element exists (added in P0-1)
- ❌ `<header>` with `role="banner"` - **MISSING**
- ❌ `<nav>` with `role="navigation"` - **MISSING**
- ❌ `<footer>` with `role="contentinfo"` - **MISSING** (if footer exists)
- ✅ `<aside>` in Sidebar (added in P0-1)

**Expected Structure:**
```svelte
<!-- +layout.svelte -->
<div class="app-container">
    <header role="banner" aria-label="Site header">
        <!-- Top navigation bar -->
    </header>

    <nav role="navigation" aria-label="Main navigation">
        <!-- Sidebar navigation -->
    </nav>

    <main role="main" id="main-content" aria-label="Main content">
        <!-- Current slot content -->
    </main>

    {#if hasFooter}
    <footer role="contentinfo" aria-label="Site footer">
        <!-- Footer content -->
    </footer>
    {/if}
</div>
```

**Impact:** HIGH - Screen readers rely on landmarks for page navigation

---

### 2.2 Heading Hierarchy

**Findings:**

#### Current Usage
```
src/lib/components/chat/MessageInput/AttachWebpageModal.svelte:40: <h1>
src/lib/components/chat/Settings/Interface/ManageFloatingActionButtonsModal.svelte:33: <h1>
src/lib/components/chat/Settings/Interface/ManageImageCompressionModal.svelte:29: <h1>
src/lib/components/chat/Settings/Interface.svelte:334: <h1> (actually should be h2)
src/lib/components/chat/Messages.svelte:451: <h2 class="sr-only">Chat Conversation</h2>
```

**Issues:**
1. Modals using `<h1>` instead of `<h2>` or `<h3>`
2. Likely missing h1 on main pages
3. Possible heading level skips (h1 → h3)

**Required Audit:**
- Check each page for single h1 (page title)
- Verify h1 → h2 → h3 progression (no skips)
- Modal headings should be h2 or h3, not h1

**Expected Structure:**
```svelte
<!-- Page level -->
<h1>Chat</h1>

<!-- Sidebar section -->
<h2>Chat History</h2>

<!-- Modal -->
<h2>Settings</h2>
<h3>Model Configuration</h3>
```

**Impact:** HIGH - Screen readers use headings for page structure navigation

---

### 2.3 Form Labels

**Audit Required:** Full scan of input/textarea/select elements

**Known Issues:**

#### MessageInput.svelte (Line 1126)
```svelte
<input
    <!-- No associated label -->
/>
```

**Pattern to Check:**
- Search for all `<input>`, `<textarea>`, `<select>` elements
- Verify each has one of:
  - Associated `<label>` element with matching `for` attribute
  - `aria-label` attribute
  - `aria-labelledby` pointing to label text
  - Wrapping `<label>` element

**Impact:** CRITICAL - Unlabeled form inputs are unusable with screen readers

---

## 3. ARIA Live Regions (WCAG 4.1.2 - Level A)

### 3.1 Current Implementation

**Existing Live Regions:** 3 instances

#### Chat Messages (Good Implementation)
```svelte
<!-- src/lib/components/chat/Messages.svelte:467 -->
<ul
    role="log"
    aria-live="polite"
    aria-relevant="additions"
    aria-atomic="false"
>
    <!-- Chat messages -->
</ul>
```
**Status:** ✅ Correctly implemented

#### NotificationToast
```svelte
<!-- src/lib/components/NotificationToast.svelte:86 -->
<div role="status">
    <!-- Toast content -->
</div>
```
**Status:** ⚠️ Partially correct - should have `aria-live="polite"`

---

### 3.2 Missing Live Regions

#### Error Messages
**Location:** Form validation errors, API errors
**Required:**
```svelte
<div
    role="alert"
    aria-live="assertive"
    class="error-message"
>
    {errorMessage}
</div>
```

#### Loading States
**Location:** Chat generation, file uploads, model loading
**Required:**
```svelte
<div
    aria-busy="true"
    aria-live="polite"
    aria-label="Loading chat response"
>
    <Spinner />
</div>
```

#### Status Announcements
**Location:** Message sent, file uploaded, settings saved
**Required:**
```svelte
<div role="status" aria-live="polite" class="sr-only">
    {statusMessage}
</div>
```

**Impact:** CRITICAL - Dynamic content changes are invisible to screen readers

---

## 4. Page Titles (WCAG 2.4.2 - Level A)

### 4.1 Current State

**Static Title:** `src/app.html:106`
```html
<title>Open WebUI</title>
```

**Issue:** Title is static and doesn't reflect current page/view

### 4.2 Required Implementation

**Dynamic Titles Needed:**
- Home: "Chat - Open WebUI"
- Specific chat: "[Chat Title] - Open WebUI"
- Settings: "Settings - Open WebUI"
- Admin: "Admin Dashboard - Open WebUI"
- User Profile: "Profile - Open WebUI"

**Implementation Location:** `src/routes/+layout.svelte` or individual page components

**Example:**
```svelte
<script>
  import { page } from '$app/stores';
  import { chatId, chats } from '$lib/stores';

  $: pageTitle = (() => {
    if ($page.route.id?.includes('/admin')) {
      return 'Admin Dashboard - Open WebUI';
    }
    if ($page.route.id?.includes('/settings')) {
      return 'Settings - Open WebUI';
    }
    if ($chatId && $chats[$chatId]) {
      return `${$chats[$chatId].title} - Open WebUI`;
    }
    return 'Chat - Open WebUI';
  })();
</script>

<svelte:head>
  <title>{pageTitle}</title>
</svelte:head>
```

**Impact:** MEDIUM - Important for browser tabs and screen reader announcements

---

## 5. Link Purpose (WCAG 2.4.4 - Level A)

### 5.1 Poor Link Text Instances

**Found:** 8+ occurrences of generic link text

#### "click here" Violations
```svelte
<!-- src/lib/components/admin/Settings/Models/Manage/ManageOllama.svelte:713 -->
<a target="_blank">{$i18n.t('click here.')}</a>

<!-- src/lib/components/admin/Settings/Audio.svelte:639 -->
{$i18n.t(`click here`, { default: 'click here' })}
```

#### Generic "learn more" Links
```svelte
<!-- src/lib/components/admin/Settings/Audio.svelte:632 -->
To learn more about SpeechT5,

<!-- src/lib/components/admin/Settings/Audio.svelte:492 -->
`Click here to learn more about faster-whisper and see the available models.`
```

### 5.2 Required Fixes

**Pattern:**
```svelte
<!-- BAD -->
<a href="/docs/models">Click here</a> to learn about models.

<!-- GOOD -->
<a href="/docs/models">Learn about model configuration</a>

<!-- BAD -->
Read more <a href="/docs/audio">here</a>.

<!-- GOOD -->
<a href="/docs/audio">Read more about audio settings</a>
```

**Impact:** MEDIUM - Links are navigable but purpose is unclear

---

## 6. State Communication (WCAG 4.1.2 - Level A)

### 6.1 Existing ARIA Pressed States

**Status:** ⚠️ **PARTIALLY IMPLEMENTED**

**Found in MessageInput.svelte:**
```svelte
<!-- Line 1714 -->
<button aria-pressed={webSearchEnabled}>
<!-- Line 1734 -->
<button aria-pressed={imageGenerationEnabled}>
<!-- Line 1756 -->
<button aria-pressed={codeInterpreterEnabled}>
```

**Status:** ✅ These 3 toggle buttons correctly use aria-pressed

### 6.2 Missing State Attributes

#### Expandable Sections
**Locations:** Settings panels, collapsible sections
**Required:**
```svelte
<button
    aria-expanded={isOpen}
    aria-controls="section-content"
    onclick={toggle}
>
    Toggle Section
</button>

<div id="section-content" hidden={!isOpen}>
    <!-- Content -->
</div>
```

#### Loading States
**Required:**
```svelte
<div aria-busy="true">
    <Spinner />
    <span class="sr-only">Loading...</span>
</div>
```

#### Selected Items
**Locations:** Model selector, chat history
**Required:**
```svelte
<div
    role="option"
    aria-selected={selected === item.id}
>
    {item.name}
</div>
```

**Impact:** HIGH - State changes must be announced to screen readers

---

## 7. Headings and Labels (WCAG 2.4.6 - Level AA)

### 7.1 Label Quality

**Audit Required:** Review all form labels for clarity

**Potential Issues:**
- Generic labels: "Name", "Value", "Settings"
- Technical jargon without explanation
- Missing labels for complex inputs

**Best Practices:**
```svelte
<!-- BAD -->
<label for="temp">Temp</label>
<input id="temp" type="number" />

<!-- GOOD -->
<label for="model-temperature">Model Temperature (0-1)</label>
<input
    id="model-temperature"
    type="number"
    min="0"
    max="1"
    step="0.1"
    aria-describedby="temp-help"
/>
<span id="temp-help">Controls randomness in responses</span>
```

**Impact:** MEDIUM - Descriptive labels improve usability

---

## 8. Error Identification (WCAG 3.3.1 - Level A)

### 8.1 Current Error Handling

**Audit Required:** Check all form validation

**Required Implementation:**
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
<span id="email-error" role="alert" class="error-text">
    {emailError}
</span>
{/if}
```

**Impact:** CRITICAL - Users must understand what went wrong

---

## 9. Additional Findings

### 9.1 Viewport Meta Tag

**Status:** ✅ **FIXED** in P0-2
- Meta viewport does NOT have `maximum-scale=1`
- Zoom is enabled for accessibility

### 9.2 Screen Reader Utilities

**Status:** ✅ **EXISTS** from P0-1
- `.sr-only` class available in `src/accessibility.css`
- Used in Messages.svelte for "Chat Conversation" heading

### 9.3 Focus Management

**Status:** ✅ **COMPLETE** from P0-1
- Modal focus trapping implemented
- Skip-to-content link exists
- Focus indicators visible

---

## Priority Implementation Plan

### P0 - Critical (Must Fix for AA Compliance)

#### 1. Image Alt Text (4-5 hours)
**Files to Modify:**
- `src/lib/components/app/AppSidebar.svelte` (2 images)
- `src/lib/components/admin/Users/UserList.svelte` (profile images)
- `src/lib/components/admin/Settings/*.svelte` (model icons)
- `src/lib/components/channel/Messages/Message.svelte` (avatars)
- `src/app.html` (splash screen images)
- ~60 additional instances across admin components

**Pattern:**
```svelte
<!-- Logo images -->
<img src="..." alt="Open WebUI Logo" />

<!-- Profile images -->
<img src={user.avatar} alt="{user.name}'s profile picture" />

<!-- Model icons -->
<img src={model.icon} alt="{model.name} logo" />

<!-- Decorative images (if any) -->
<img src="..." alt="" role="presentation" />
```

#### 2. ARIA Live Regions (4-5 hours)
**Components to Modify:**
- `src/lib/components/NotificationToast.svelte` - Add aria-live="polite"
- Form validation components - Add role="alert", aria-live="assertive"
- Loading spinners - Add aria-busy="true", descriptive labels
- Status messages - Add role="status", aria-live="polite"

#### 3. Form Labels (3-4 hours)
**Audit Process:**
1. Find all inputs: `grep -rn "<input\|<textarea\|<select" src/lib/components/`
2. Verify each has label or aria-label
3. Add missing labels
4. Associate errors with aria-describedby

#### 4. Heading Hierarchy (2-3 hours)
**Process:**
1. Add h1 to main pages
2. Convert modal h1 to h2/h3
3. Verify no level skips
4. Test with heading navigation

**Total P0 Time:** 13-17 hours

---

### P1 - Important (Should Fix Post-Compliance)

#### 5. Link Text Quality (1-2 hours)
- Replace all "click here" links
- Make "learn more" links descriptive

#### 6. Page Titles (1 hour)
- Implement dynamic title updates
- Test title changes on navigation

#### 7. State Attributes (2-3 hours)
- Add aria-expanded to collapsible sections
- Add aria-selected to list items
- Add aria-busy to loading states

**Total P1 Time:** 4-6 hours

---

### P2 - Enhancement (Nice to Have)

#### 8. Semantic Landmarks (1-2 hours)
- Add `<header role="banner">`
- Add `<nav role="navigation">`
- Add `<footer role="contentinfo">` (if applicable)

#### 9. Label Quality (1-2 hours)
- Review all labels for clarity
- Add help text for complex inputs

**Total P2 Time:** 2-4 hours

---

## Testing Strategy

### Automated Testing

```bash
# Install axe-core for ARIA testing
npm install -D @axe-core/playwright

# Run ARIA audit
npx playwright test tests/accessibility/screen-reader.spec.ts

# Check for ARIA violations
npx axe http://localhost:3000 --tags wcag2a,wcag2aa --save axe-aria.json
```

### Manual Screen Reader Testing

**Tool:** Orca (Linux native)

**Test Scenarios:**
1. Navigate entire app using only screen reader
2. Tab through all interactive elements
3. Send a chat message and verify announcement
4. Select a model from dropdown
5. Open and close modal
6. Trigger form validation error
7. View error message announcement

**Success Criteria:**
- All images have appropriate alt text or are marked decorative
- All buttons announce their purpose
- Dynamic content changes are announced
- Form errors are announced
- Heading structure is logical
- No "unlabeled" or "unidentified" elements

---

## Risk Assessment

### High Risk
- **69 images without alt text:** Large scope, requires careful review
- **Missing ARIA live regions:** May require refactoring of state management
- **Form label associations:** Scattered across many components

### Medium Risk
- **Heading hierarchy:** May have architectural implications
- **Link text quality:** Requires i18n updates
- **Page titles:** Needs integration with routing

### Low Risk
- **ARIA pressed states:** Partially implemented, just need more coverage
- **Semantic landmarks:** Simple wrapper changes

---

## Dependencies

### Required Before Starting
- ✅ P0-1 (Keyboard Navigation) - Complete
- ⏳ P0-2 (Color Contrast) - Can proceed in parallel

### Tools
- Orca screen reader (available on Linux)
- axe-core for automated testing
- Firefox/Chrome browser
- Playwright for E2E tests

---

## Success Metrics

P0-3 is complete when:

- [ ] All 69 images have alt text or role="presentation"
- [ ] ARIA live regions cover: chat messages, errors, status, loading
- [ ] All form inputs have associated labels
- [ ] Heading hierarchy is h1 → h2 → h3 with no skips
- [ ] All toggle buttons have aria-pressed
- [ ] All expandable sections have aria-expanded
- [ ] Page titles are dynamic and descriptive
- [ ] No generic "click here" link text
- [ ] axe-core scan: 0 ARIA violations
- [ ] Manual screen reader test: All key flows pass
- [ ] Orca announces all interactive elements correctly
- [ ] Dynamic content changes are announced

---

## Next Steps

1. **Immediate:** Create detailed implementation plan (`P0-3-implementation-plan.md`)
2. **Week 3:** Begin implementation after P0-2 color contrast is underway
3. **Week 3:** Parallel track: automated tests + manual testing
4. **Week 4:** Final validation with screen reader
5. **April 18-24:** Integration testing and final compliance check

---

## References

- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [WAI-ARIA 1.2 Specification](https://www.w3.org/TR/wai-aria-1.2/)
- [MDN: ARIA Live Regions](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/ARIA_Live_Regions)
- [WebAIM: Screen Reader Testing](https://webaim.org/articles/screenreader_testing/)
- [axe-core Rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)

---

**Audit Complete:** March 28, 2026
**Next Document:** P0-3 Implementation Plan
