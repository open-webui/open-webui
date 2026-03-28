# Open-WebUI Accessibility Documentation

This directory contains documentation for WCAG 2.1 AA accessibility compliance efforts in Open-WebUI.

---

## Quick Links

- **[Progress Tracker](./PROGRESS.md)** - Current status, completed tasks, and timeline
- **[Testing Guide](./TESTING.md)** - How to run accessibility tests (manual and automated)
- **[Implementation Notes](./IMPLEMENTATION.md)** - Technical details of accessibility features

---

## Overview

**Legal Deadline:** April 24, 2026
**Target:** WCAG 2.1 Level AA compliance
**Current Status:** P0-1 Keyboard Navigation (80% complete)

Open-WebUI is implementing comprehensive accessibility improvements to achieve WCAG 2.1 AA compliance before the April 24, 2026 legal deadline. This work is being tracked in GitHub issue/task #23.

---

## Accessibility Features Implemented

### Phase 1: Keyboard Navigation (Current)

✅ **Completed:**
- Enhanced Modal component with ARIA labels and keyboard handling
- Improved Sidebar component with focus management
- Skip-to-content link for bypass blocks (WCAG 2.4.1)
- Global keyboard focus indicators (2px solid outline, high contrast)
- Escape key closes modals and sidebars
- Reduced motion support (prefers-reduced-motion)
- Screen reader utilities (.sr-only class)

⏳ **In Progress:**
- Icon-only buttons need ARIA labels
- Arrow key navigation for lists/dropdowns
- Automated keyboard navigation tests

❌ **Not Started:**
- Color contrast fixes (P0-2)
- Screen reader support enhancements (P0-3)
- ARIA live regions for dynamic content
- Heading hierarchy audit

---

## WCAG 2.1 AA Guidelines Addressed

### Level A (Must Have)

| Guideline | Status | Implementation |
|-----------|--------|----------------|
| 1.1.1 Non-text Content | ⏳ Partial | Icon buttons need aria-label, images need alt |
| 1.3.1 Info and Relationships | ✅ In Progress | ARIA landmarks, semantic HTML |
| 1.3.2 Meaningful Sequence | ✅ Complete | Tab order follows visual flow |
| 2.1.1 Keyboard | ✅ In Progress | All functionality keyboard-accessible |
| 2.1.2 No Keyboard Trap | ✅ Complete | Focus trap in modals, can exit with Esc |
| 2.4.1 Bypass Blocks | ✅ Complete | Skip-to-content link |
| 2.4.2 Page Titled | ✅ Complete | Title set in +layout.svelte |
| 2.4.7 Focus Visible | ✅ Complete | 2px solid outline, high contrast |
| 3.1.1 Language of Page | ✅ Complete | i18n support, locale detection |

### Level AA (Must Have for Compliance)

| Guideline | Status | Implementation |
|-----------|--------|----------------|
| 1.4.3 Contrast (Minimum) | ❌ Not Started | Need color contrast audit |
| 1.4.5 Images of Text | ✅ Complete | No images of text used |
| 2.4.6 Headings and Labels | ⏳ Partial | Some labels present, need audit |
| 2.4.7 Focus Visible | ✅ Complete | Global focus indicators |
| 3.2.3 Consistent Navigation | ✅ Complete | Navigation consistent |
| 3.2.4 Consistent Identification | ✅ Complete | Icons/buttons consistent |
| 3.3.3 Error Suggestion | ⏳ Partial | Some error handling, needs enhancement |
| 3.3.4 Error Prevention | ⏳ Partial | Confirmation dialogs exist |

---

## Testing Accessibility

### Manual Testing

#### Keyboard Navigation Test
1. Unplug your mouse
2. Tab through the entire application
3. Verify:
   - All interactive elements reachable
   - Focus indicators visible (2px outline)
   - Escape closes modals/sidebars
   - Enter activates buttons/links
   - Skip-to-content link appears on first Tab

#### Screen Reader Test (Linux)
```bash
# Install Orca screen reader
sudo apt install orca

# Start Orca
orca --enable=speech

# Navigate Open-WebUI with keyboard
# Verify all content is announced
```

#### Color Contrast Test
1. Install axe DevTools Chrome extension
2. Open Open-WebUI in Chrome
3. Open DevTools → axe tab
4. Click "Scan ALL of my page"
5. Review color contrast violations
6. Fix using WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/

### Automated Testing

#### Lighthouse Accessibility Audit
```bash
# Scan local development server
lighthouse http://localhost:3000 \
  --only-categories=accessibility \
  --output=html \
  --output-path=./lighthouse-report.html

# Scan production
lighthouse https://chat.spooty.io \
  --only-categories=accessibility \
  --output=html \
  --output-path=./lighthouse-prod-report.html

# Target: 90+ score
```

#### axe-core Scan
```bash
# Install axe-core CLI
npm install -g @axe-core/cli

# Scan for violations
npx axe --chrome-options="headless" http://localhost:3000 \
  --save results.json

# Check for color contrast violations specifically
jq '.violations[] | select(.id=="color-contrast")' results.json

# Target: 0 critical violations
```

#### Playwright Accessibility Tests
```bash
# Run accessibility test suite (when implemented)
npm run test:accessibility

# Or run specific test file
npx playwright test tests/accessibility/keyboard-navigation.spec.ts
```

---

## Keyboard Shortcuts Reference

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Move focus to next interactive element |
| `Shift+Tab` | Move focus to previous interactive element |
| `Enter` | Activate focused button/link |
| `Escape` | Close modal or sidebar |
| `Space` | Toggle focused checkbox or button |

### Chat Interface

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message (if `ctrlEnterToSend` disabled) |
| `Ctrl+Enter` | Send message (if `ctrlEnterToSend` enabled) |
| `Shift+Enter` | New line in message input |
| `Escape` | Stop AI response or clear selections |
| `↑` (when input empty) | Edit last user message |

### Navigation

| Shortcut | Action |
|----------|--------|
| `Tab` (first) | Show skip-to-content link |
| `Enter` (on skip link) | Jump to main chat interface |

---

## Resources

### WCAG 2.1 Guidelines
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [Understanding WCAG 2.1](https://www.w3.org/WAI/WCAG21/Understanding/)
- [How to Meet WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/)

### Testing Tools
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [axe DevTools Chrome Extension](https://chrome.google.com/webstore/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd)
- [WAVE Browser Extension](https://wave.webaim.org/extension/)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)

### Screen Readers
- **Linux:** Orca (`sudo apt install orca`)
- **macOS:** VoiceOver (built-in, `Cmd+F5` to toggle)
- **Windows:** NVDA (free, https://www.nvaccess.org/)
- **Windows:** JAWS (commercial, https://www.freedomscientific.com/products/software/jaws/)

### ARIA Authoring Practices
- [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)
- [ARIA Roles](https://www.w3.org/WAI/PF/aria/roles)
- [ARIA States and Properties](https://www.w3.org/WAI/PF/aria/states_and_properties)

---

## Contributing to Accessibility

When adding new features or components to Open-WebUI, follow these accessibility guidelines:

### Checklist for New Components

- [ ] All interactive elements are keyboard-accessible
- [ ] Focus indicators are visible (use global focus styles)
- [ ] Icon-only buttons have `aria-label`
- [ ] Images have `alt` text (or `alt=""` if decorative)
- [ ] Color is not the only means of conveying information
- [ ] Text has sufficient color contrast (4.5:1 minimum)
- [ ] Form inputs have associated labels
- [ ] Error messages are associated with fields via `aria-describedby`
- [ ] Dynamic content uses ARIA live regions
- [ ] Semantic HTML is used (e.g., `<button>` not `<div onclick>`)
- [ ] Modals trap focus and can be closed with Escape
- [ ] Component tested with keyboard only
- [ ] Component tested with screen reader

### Code Examples

#### Icon-Only Button with ARIA Label
```svelte
<button aria-label="Send message" on:click={handleSend}>
  <SendIcon className="size-5" />
</button>
```

#### Form Input with Label
```svelte
<label for="username">Username</label>
<input
  id="username"
  type="text"
  aria-required="true"
  aria-invalid={hasError}
  aria-describedby={hasError ? "username-error" : undefined}
/>
{#if hasError}
  <span id="username-error" role="alert">
    Username is required
  </span>
{/if}
```

#### ARIA Live Region for Notifications
```svelte
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
  class="sr-only"
>
  {statusMessage}
</div>
```

#### Skip-to-Content Link (Already Implemented)
```svelte
<a href="#main-content" class="skip-to-content">
  Skip to main content
</a>

<main id="main-content" role="main" aria-label="Chat interface">
  <!-- Main content here -->
</main>
```

---

## Contact & Support

For questions or issues related to accessibility:
- GitHub Issue: #23 (WCAG 2.1 AA compliance)
- Feature Branch: `feat/wcag-phase1-accessibility`
- Documentation: `/docs/accessibility/`

---

## Changelog

### 2026-03-28: Phase 1 Initial Implementation
- Enhanced Modal component with ARIA labels
- Improved Sidebar keyboard navigation
- Added skip-to-content link
- Created global accessibility.css stylesheet
- Documented progress and testing procedures
