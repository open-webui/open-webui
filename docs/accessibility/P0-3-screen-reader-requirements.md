# P0-3: Screen Reader Support - WCAG 2.1 AA Requirements

**Document Version:** 1.0
**Created:** March 28, 2026
**Deadline:** April 24, 2026 (27 days remaining)
**Status:** Requirements Analysis Complete

---

## Executive Summary

This document outlines the WCAG 2.1 Level A and AA success criteria specifically related to screen reader support. These requirements are CRITICAL for legal compliance by April 24, 2026.

**Estimated Implementation Time:** 15-20 hours
**Priority:** P0 (Critical - Required for compliance)
**Dependencies:** P0-1 (Keyboard Navigation) must be complete

---

## WCAG 2.1 Success Criteria for Screen Readers

### Level A Requirements (MANDATORY)

#### 1.1.1 Non-text Content (Level A)

**Requirement:** All non-text content that is presented to the user has a text alternative that serves the equivalent purpose.

**Implementation:**
- All `<img>` elements MUST have `alt` attribute
- Functional images: Descriptive alt text (describes purpose/action)
- Decorative images: `alt=""` OR `role="presentation"` OR `aria-hidden="true"`
- Icon buttons: `aria-label` describing the action
- SVG icons: Use `<title>` or `aria-label` on parent element

**Examples:**
```html
<!-- Functional image -->
<img src="/logo.svg" alt="Open WebUI Logo" />

<!-- Decorative image -->
<img src="/decoration.svg" alt="" />
<!-- OR -->
<img src="/decoration.svg" role="presentation" />

<!-- Icon button -->
<button aria-label="Send message">
  <SendIcon />
</button>
```

**Testing:** Screen reader should announce meaningful description, or skip decorative images entirely.

---

#### 1.3.1 Info and Relationships (Level A)

**Requirement:** Information, structure, and relationships conveyed through presentation can be programmatically determined or are available in text.

**Implementation:**

1. **Semantic HTML Structure:**
   - Use proper heading hierarchy (h1 → h2 → h3, no skipping levels)
   - Use `<nav>`, `<main>`, `<header>`, `<footer>`, `<aside>`, `<article>`
   - Use `<ul>`/`<ol>`/`<li>` for lists
   - Use `<table>`, `<th>`, `<caption>` for data tables

2. **Form Labels:**
   - All `<input>`, `<textarea>`, `<select>` MUST have associated `<label>`
   - Use `<label for="input-id">` or wrap input inside label
   - Use `aria-labelledby` or `aria-label` when visual label doesn't exist

3. **ARIA Roles:**
   - Use semantic HTML first, ARIA second
   - Don't override semantic roles unnecessarily
   - Use `role="dialog"` for modals
   - Use `role="complementary"` for sidebars

**Examples:**
```html
<!-- Good: Semantic form -->
<form>
  <label for="chat-input">Enter your message</label>
  <textarea id="chat-input" />
</form>

<!-- Bad: No programmatic association -->
<form>
  <span>Enter your message</span>
  <textarea />
</form>

<!-- Good: Heading hierarchy -->
<h1>Open WebUI</h1>
<h2>Chat Conversation</h2>
<h3>Model Settings</h3>

<!-- Bad: Skipped heading level -->
<h1>Open WebUI</h1>
<h4>Chat Conversation</h4>
```

**Testing:** Screen reader should correctly announce relationships (e.g., "Username, edit text" for labeled input).

---

#### 2.4.1 Bypass Blocks (Level A)

**Requirement:** A mechanism is available to bypass blocks of content that are repeated on multiple Web pages.

**Status:** ✅ **ALREADY IMPLEMENTED** in P0-1 (skip-to-content link)

**Verification:**
- Skip-to-content link appears on first Tab press
- Link jumps to `#main-content` landmark
- Main content area has `role="main"` and `aria-label`

---

#### 2.4.2 Page Titled (Level A)

**Requirement:** Web pages have titles that describe topic or purpose.

**Implementation:**
- Update `<title>` tag dynamically based on page/view
- Chat page: "Chat - Open WebUI"
- Settings page: "Settings - Open WebUI"
- Specific chat: "[Chat Title] - Open WebUI"

**Current Status:** Need to audit `src/routes/+layout.svelte` and page components for dynamic title updates.

**Example:**
```svelte
<script>
  import { page } from '$app/stores';

  $: pageTitle = $page.route.id === '/chat'
    ? 'Chat - Open WebUI'
    : $page.route.id === '/settings'
    ? 'Settings - Open WebUI'
    : 'Open WebUI';
</script>

<svelte:head>
  <title>{pageTitle}</title>
</svelte:head>
```

**Testing:** Browser tab title should describe current page/view.

---

#### 2.4.3 Focus Order (Level A)

**Requirement:** If a Web page can be navigated sequentially and the navigation sequences affect meaning or operation, focusable components receive focus in an order that preserves meaning and operability.

**Status:** ✅ **MOSTLY COMPLETE** from P0-1

**Verification Required:**
- Tab order follows visual layout (left-to-right, top-to-bottom)
- Modal focus doesn't escape modal container
- Sidebar focus returns to trigger element when closed
- No "focus traps" except intentional (modals)

**Testing:** Tab through entire application and verify logical flow.

---

#### 2.4.4 Link Purpose (Level A)

**Requirement:** The purpose of each link can be determined from the link text alone or from the link text together with its programmatically determined link context.

**Implementation:**
- Avoid generic link text: "click here", "read more", "learn more"
- Link text should describe destination: "View settings", "Open documentation", "Go to chat history"
- For icon-only links, use `aria-label`

**Audit Required:** Search codebase for generic link text patterns.

**Examples:**
```html
<!-- Good: Descriptive link text -->
<a href="/docs/accessibility">Read accessibility documentation</a>

<!-- Bad: Generic link text -->
<a href="/docs/accessibility">Click here</a>

<!-- Good: Icon link with aria-label -->
<a href="/settings" aria-label="Open settings">
  <SettingsIcon />
</a>
```

**Testing:** Screen reader should announce clear destination for every link.

---

#### 3.2.4 Consistent Identification (Level AA)

**Requirement:** Components that have the same functionality within a set of Web pages are identified consistently.

**Implementation:**
- Use same labels for same functions across pages
- "Send message" button always labeled "Send message"
- "Settings" icon always labeled "Settings" or "Open settings"
- Consistency in button labels, link text, form labels

**Audit Required:** Document all repeated UI elements and verify consistent labeling.

**Testing:** Navigate between different pages/views, verify same elements have same labels.

---

#### 3.3.1 Error Identification (Level A)

**Requirement:** If an input error is automatically detected, the item that is in error is identified and the error is described to the user in text.

**Implementation:**

1. **Form Validation Errors:**
   - Error messages MUST be visible text (not just color/icon)
   - Associate error with input via `aria-describedby`
   - Use `aria-invalid="true"` on invalid inputs

2. **API/Server Errors:**
   - Display error messages in text
   - Consider `role="alert"` for immediate errors
   - Don't rely solely on toast notifications

**Examples:**
```html
<!-- Good: Error programmatically associated -->
<label for="email">Email</label>
<input
  id="email"
  type="email"
  aria-invalid="true"
  aria-describedby="email-error"
/>
<span id="email-error" role="alert">
  Please enter a valid email address
</span>

<!-- Bad: Error not associated with input -->
<label for="email">Email</label>
<input id="email" type="email" class="error" />
<span class="error-text">Invalid email</span>
```

**Testing:** Screen reader should announce error message when focusing invalid field.

---

#### 3.3.2 Labels or Instructions (Level A)

**Requirement:** Labels or instructions are provided when content requires user input.

**Implementation:**
- All form inputs have visible labels
- Complex inputs have instructions (e.g., password requirements)
- Multi-step forms indicate current step and total steps

**Audit Required:** Review all form inputs for proper labeling.

**Examples:**
```html
<!-- Good: Label + instructions -->
<label for="password">Password</label>
<span id="password-hint">
  Must be at least 8 characters with 1 number
</span>
<input
  id="password"
  type="password"
  aria-describedby="password-hint"
/>
```

**Testing:** Screen reader announces label and instructions when focusing input.

---

#### 4.1.2 Name, Role, Value (Level A)

**Requirement:** For all user interface components, the name and role can be programmatically determined; states, properties, and values that can be set by the user can be programmatically set; and notification of changes to these items is available to user agents, including assistive technologies.

**Implementation:**

1. **All Interactive Elements:**
   - Buttons: Use `<button>` (has implicit role)
   - Links: Use `<a>` with `href` (has implicit role)
   - Custom controls: Add explicit `role` attribute

2. **Accessible Names:**
   - Text content: `<button>Send</button>`
   - ARIA label: `<button aria-label="Send message"><SendIcon /></button>`
   - ARIA labelledby: `<button aria-labelledby="send-label"><span id="send-label">Send</span></button>`

3. **State Communication:**
   - Toggles: `aria-pressed="true"` or `aria-pressed="false"`
   - Expandable: `aria-expanded="true"` or `aria-expanded="false"`
   - Selected: `aria-selected="true"` for selected items
   - Checked: `aria-checked="true"` for checkboxes
   - Disabled: `disabled` attribute or `aria-disabled="true"`
   - Loading: `aria-busy="true"`

4. **ARIA Live Regions:**
   - Chat messages streaming: `aria-live="polite"`
   - Error announcements: `aria-live="assertive"`
   - Status updates: `role="status"`, `aria-live="polite"`

**Examples:**
```html
<!-- Toggle button with state -->
<button
  aria-label="Enable web search"
  aria-pressed="false"
  onclick="toggleWebSearch()"
>
  <SearchIcon />
</button>

<!-- Loading state -->
<div aria-busy="true" aria-label="Loading chat history">
  <Spinner />
</div>

<!-- Live region for chat messages -->
<div
  role="log"
  aria-live="polite"
  aria-atomic="false"
  aria-label="Chat conversation"
>
  {#each messages as message}
    <article aria-label="{message.role} message">
      {@html message.content}
    </article>
  {/each}
</div>

<!-- Status announcement -->
<div role="status" aria-live="polite" class="sr-only">
  Message sent successfully
</div>
```

**Testing:** Screen reader should announce name, role, and current state for all controls.

---

### Level AA Requirements (MANDATORY)

#### 2.4.6 Headings and Labels (Level AA)

**Requirement:** Headings and labels describe topic or purpose.

**Implementation:**
- Heading text clearly describes following content
- Form labels clearly describe input purpose
- Section headings are descriptive, not generic

**Audit Required:**
- Review all heading text for clarity
- Check all form labels for descriptiveness

**Examples:**
```html
<!-- Good: Descriptive headings -->
<h2>Model Selection</h2>
<h2>Chat History</h2>

<!-- Bad: Generic headings -->
<h2>Options</h2>
<h2>Items</h2>

<!-- Good: Descriptive labels -->
<label for="model-temp">Model Temperature (0-1)</label>

<!-- Bad: Unclear labels -->
<label for="model-temp">Temp</label>
```

**Testing:** Screen reader user should understand purpose without additional context.

---

#### 3.2.4 Consistent Navigation (Level AA)

**Requirement:** Navigational mechanisms that are repeated on multiple Web pages within a set of Web pages occur in the same relative order each time they are repeated, unless a change is initiated by the user.

**Implementation:**
- Sidebar navigation menu: Same order on all pages
- Header navigation: Same position and order
- Footer links: Consistent across pages

**Status:** Likely already compliant (single-page app with consistent layout)

**Verification:** Navigate between different views/pages, verify navigation consistency.

---

## Implementation Priority

### Critical (Must Fix for AA Compliance)

1. **Image Alt Text** (3-4 hours)
   - All functional images need descriptive alt
   - All decorative images need alt="" or role="presentation"

2. **ARIA Live Regions** (4-6 hours)
   - Chat streaming: aria-live="polite"
   - Error messages: aria-live="assertive"
   - Loading states: aria-busy="true"

3. **Form Label Associations** (2-3 hours)
   - All inputs have proper labels
   - Error messages use aria-describedby

4. **Heading Hierarchy** (2-3 hours)
   - Fix any skipped heading levels
   - Ensure logical structure

5. **Link Text Quality** (1-2 hours)
   - Remove generic "click here" text
   - Add aria-labels to icon-only links

6. **Page Titles** (1 hour)
   - Dynamic title updates based on view

7. **State Announcements** (2-3 hours)
   - Toggle buttons: aria-pressed
   - Expandable sections: aria-expanded
   - Loading states: aria-busy

**Total Estimated: 15-22 hours**

### Important (Should Fix Post-Compliance)

1. Consistent identification audit
2. Instructions for complex inputs
3. Enhanced error messages

---

## Testing Requirements

### Screen Reader Testing

**Tools:**
- **Linux:** Orca (primary, native to environment)
- **Windows:** NVDA (if VM available)
- **macOS:** VoiceOver (if available)

**Test Scenarios:**
1. Navigate entire app with screen reader only
2. Send a chat message
3. Select a different model
4. Open and close settings modal
5. View chat history
6. Handle form validation errors

**Success Criteria:**
- All interactive elements have clear names
- All images have appropriate alt text
- All dynamic content changes are announced
- All form fields have labels
- Heading hierarchy is logical
- No "unlabeled button" or "unlabeled image" announcements

### Automated Testing

**Tools:**
- axe-core via Playwright
- @axe-core/cli

**Tests:**
```bash
# Run automated screen reader tests
npx playwright test tests/accessibility/screen-reader.spec.ts

# Check for ARIA issues with axe
npx axe http://localhost:3000 --tags wcag2a,wcag2aa --save axe-aria.json
```

**Target:** 0 ARIA-related violations

---

## Success Criteria

P0-3 is COMPLETE when:

- [ ] All Level A criteria met
- [ ] All Level AA criteria met
- [ ] axe-core scan: 0 ARIA violations
- [ ] Manual screen reader testing: All key flows pass
- [ ] All images have alt text
- [ ] All buttons have accessible names
- [ ] All forms have proper labels
- [ ] Heading hierarchy is correct
- [ ] ARIA live regions announce dynamic content
- [ ] State changes are communicated (aria-pressed, aria-expanded, aria-busy)
- [ ] Link text is descriptive
- [ ] Page titles are descriptive and dynamic

---

## Dependencies

**Required Before Starting:**
- ✅ P0-1 (Keyboard Navigation) complete
- ⏳ P0-2 (Color Contrast) in progress (can proceed in parallel)

**Resources Needed:**
- Screen reader: Orca (already available on Linux)
- Browser: Firefox with screen reader support
- Testing time: 6-8 hours for manual testing

---

## Risk Assessment

### High Risk
- Unknown number of images without alt text (requires full audit)
- Chat streaming may need significant refactoring for aria-live
- Form validation error handling may need updates

### Medium Risk
- Heading hierarchy may have several violations
- Some custom components may need role attributes
- Link text quality may require many small fixes

### Low Risk
- Page titles (simple implementation)
- ARIA pressed states (already partially implemented in MessageInput)
- Semantic landmarks (mostly already present from P0-1)

---

## References

- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [MDN: ARIA](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA)
- [WebAIM: Screen Reader Testing](https://webaim.org/articles/screenreader_testing/)
- [Deque axe-core Rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)

---

## Next Steps

1. Create `P0-3-open-webui-screen-reader-audit.md` (audit current state)
2. Create `P0-3-implementation-plan.md` (detailed task breakdown)
3. Begin implementation after P0-2 is underway
