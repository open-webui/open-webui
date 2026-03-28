# WCAG 2.1 AA Color Contrast Fixes Needed

**Date:** March 28, 2026
**Status:** Manual audit in progress
**Total Violations Found:** 770 instances of `text-gray-[456]00` classes
**Priority:** P0 - CRITICAL (April 24 deadline)

---

## Executive Summary

### Scope of Issue
- **Total instances:** 770 uses of potentially problematic gray text classes
- **Primary culprits:** `text-gray-500`, `text-gray-600`, `text-gray-400`
- **Affected components:** 194 Svelte files across the entire codebase

### WCAG 2.1 AA Requirements
- **Normal text (< 18pt):** Minimum 4.5:1 contrast ratio
- **Large text (≥ 18pt):** Minimum 3:1 contrast ratio
- **UI components:** Minimum 3:1 contrast ratio

---

## Tailwind Default Gray Scale Contrast Analysis

### Dark Mode (#111827 / gray-900 background)

| Class | Hex Value | Contrast Ratio | Status | Recommended Fix |
|-------|-----------|----------------|--------|----------------|
| `text-gray-300` | `#d1d5db` | 7.9:1 | ✅ PASS | Use as-is |
| `text-gray-400` | `#9ca3af` | 5.1:1 | ✅ PASS | Use as-is |
| `text-gray-500` | `#6b7280` | **2.8:1** | ❌ **FAIL** | Replace with `text-gray-400` or lighter |
| `text-gray-600` | `#4b5563` | **1.9:1** | ❌ **FAIL** | Replace with `text-gray-300` |

### Light Mode (#ffffff / white background)

| Class | Hex Value | Contrast Ratio | Status | Recommended Fix |
|-------|-----------|----------------|--------|----------------|
| `text-gray-700` | `#374151` | 10.5:1 | ✅ PASS | Use as-is |
| `text-gray-600` | `#4b5563` | 7.5:1 | ✅ PASS | Use as-is |
| `text-gray-500` | `#6b7280` | 4.6:1 | ✅ PASS (barely) | Acceptable |
| `text-gray-400` | `#9ca3af` | **2.8:1** | ❌ **FAIL** | Replace with `text-gray-600` |

---

## Critical Pattern: Dark Mode Double-Class Usage

**MOST COMMON PATTERN (HIGH PRIORITY FIX):**
```svelte
class="text-gray-600 dark:text-gray-400"
```

**Analysis:**
- **Light mode:** `text-gray-600` = 7.5:1 ✅ PASS
- **Dark mode:** `text-gray-400` = 5.1:1 ✅ PASS
- **Status:** ✅ **SAFE - NO CHANGE NEEDED**

**PROBLEMATIC PATTERN:**
```svelte
class="text-gray-500"
```

**Analysis:**
- **Light mode:** 4.6:1 ✅ PASS (barely)
- **Dark mode:** 2.8:1 ❌ **CRITICAL FAIL**
- **Fix:** Change to `text-gray-600 dark:text-gray-400`

---

## Component-Specific Violations

### High-Impact Components

#### 1. Sidebar.svelte (3 violations)

**Line 894:**
```svelte
class="sidebar px-[0.5625rem] pt-2 pb-1.5 flex justify-between space-x-1 text-gray-600 dark:text-gray-400 sticky top-0 z-10 -mb-3"
```
- **Status:** ✅ SAFE (uses dark mode override)
- **No fix needed**

**Line 1228:**
```svelte
buttonClassName=" text-gray-500"
```
- **Impact:** HIGH (button visibility)
- **Context:** Button text in sidebar
- **Fix:** Change to `text-gray-600 dark:text-gray-400`
- **Contrast:** Current 2.8:1 → Fixed 5.1:1 (dark mode)

**Line 1313:**
```svelte
class="w-full pl-2.5 text-xs text-gray-500 dark:text-gray-500 font-medium"
```
- **Impact:** CRITICAL (same class for both modes!)
- **Context:** Small text (text-xs) - needs EVEN BETTER contrast
- **Fix:** Change to `text-gray-600 dark:text-gray-400`
- **Contrast:** Current 2.8:1 → Fixed 5.1:1 (dark mode)

#### 2. Navbar.svelte (4 violations)

**Line 92, 120, 183:**
```svelte
class="text-gray-600 dark:text-gray-400"
```
- **Status:** ✅ SAFE (uses dark mode override)
- **No fix needed**

**Line 268:**
```svelte
<div class="text-xs text-gray-500">{$i18n.t('Temporary Chat')}</div>
```
- **Impact:** MEDIUM (informational text)
- **Context:** "Temporary Chat" indicator
- **Fix:** Change to `text-gray-600 dark:text-gray-400`
- **Note:** Small text (text-xs) on gray background = extra concern

---

## Systematic Fix Strategy

### Phase 1: Find and Replace (Bulk Fixes)

**Strategy:** Use global find-replace for the most common failing patterns.

#### Fix 1: Standalone `text-gray-500` (no dark mode override)

**Find:** `text-gray-500"` (note: ends with quote to avoid matching `dark:text-gray-500`)

**Replace:** `text-gray-600 dark:text-gray-400"`

**Estimated instances:** ~200-300

**Risk:** Low - improves contrast in both modes

#### Fix 2: `dark:text-gray-500` (explicit dark mode failure)

**Find:** `dark:text-gray-500`

**Replace:** `dark:text-gray-400`

**Estimated instances:** ~50

**Risk:** Very low - only affects dark mode

#### Fix 3: `text-gray-600` (light mode only - needs dark override)

**Find:** `text-gray-600"` followed by NO dark: override

**Replace:** `text-gray-600 dark:text-gray-400"`

**Approach:** Manual review (context-dependent)

---

## Safe Color Pairs Reference

### Dark Mode (#111827 background)

| Use Case | Class | Contrast | Status |
|----------|-------|----------|--------|
| Primary text | `text-white` | 17.1:1 | ✅ Excellent |
| Secondary text | `text-gray-200` | 10.4:1 | ✅ Excellent |
| Tertiary text | `text-gray-300` | 7.9:1 | ✅ Good |
| Interactive elements | `text-gray-400` | 5.1:1 | ✅ Minimum |
| **AVOID** | `text-gray-500` | 2.8:1 | ❌ Fail |
| **NEVER USE** | `text-gray-600` | 1.9:1 | ❌ Critical fail |

### Light Mode (#ffffff background)

| Use Case | Class | Contrast | Status |
|----------|-------|----------|--------|
| Primary text | `text-gray-900` | 17.1:1 | ✅ Excellent |
| Secondary text | `text-gray-800` | 12.6:1 | ✅ Excellent |
| Tertiary text | `text-gray-700` | 10.5:1 | ✅ Good |
| Interactive elements | `text-gray-600` | 7.5:1 | ✅ Good |
| Minimum safe | `text-gray-500` | 4.6:1 | ⚠️ Barely passes |
| **AVOID** | `text-gray-400` | 2.8:1 | ❌ Fail |

---

## Implementation Plan

### Step 1: Automated Replacements (2-3 hours)

Use VSCode find-replace with regex:

1. **Find:** `(\s)text-gray-500(["'])`
   **Replace:** `$1text-gray-600 dark:text-gray-400$2`
   **Where:** All `.svelte` files in `src/lib/components`

2. **Find:** `dark:text-gray-500`
   **Replace:** `dark:text-gray-400`
   **Where:** All `.svelte` files

3. **Test:** `npm run build` after each batch

### Step 2: Manual Review of Edge Cases (2-3 hours)

**Components requiring manual inspection:**
- Modal.svelte (overlays have complex backgrounds)
- MessageInput.svelte (1,940 lines, many interactive elements)
- Settings pages (admin sections)

**Check for:**
- Disabled states (may intentionally be low contrast)
- Decorative elements (may not need fixing)
- Elements with custom backgrounds (need context-specific contrast)

### Step 3: Build Verification (1 hour)

1. Run `npm run build`
2. Fix any TypeScript/Svelte compilation errors
3. Visual regression check (compare before/after screenshots)

### Step 4: Post-Deployment Validation (2-3 hours)

1. Deploy to local dev environment
2. Run axe-core browser extension scan
3. Manual spot-check with color picker
4. Document any remaining violations

---

## Acceptance Criteria

✅ All `text-gray-500` standalone instances fixed
✅ All `dark:text-gray-500` instances fixed
✅ All small text (text-xs) meets 4.5:1 minimum
✅ Build passes without errors
✅ Visual hierarchy maintained
✅ Both light and dark modes validated

---

## Risk Assessment

### Low Risk Changes
- `text-gray-500` → `text-gray-600 dark:text-gray-400` (universal improvement)
- `dark:text-gray-500` → `dark:text-gray-400` (dark mode only)

### Medium Risk Changes
- Components with custom backgrounds (need context analysis)
- Disabled states (may need separate handling)

### High Risk Changes
- None identified (all fixes improve accessibility)

---

## Timeline

| Phase | Duration | Target Completion |
|-------|----------|------------------|
| Automated replacements | 2-3 hours | Today (March 28) |
| Manual edge case review | 2-3 hours | Today (March 28) |
| Build verification | 1 hour | Today (March 28) |
| Documentation | 1 hour | Today (March 28) |
| **Total** | **6-8 hours** | **End of day March 28** |

---

## Next Steps

1. ✅ Create this audit document
2. ⏳ Run automated find-replace for `text-gray-500` patterns
3. ⏳ Run automated find-replace for `dark:text-gray-500` patterns
4. ⏳ Test build after each batch
5. ⏳ Manual review of MessageInput.svelte and Modal.svelte
6. ⏳ Final build verification
7. ⏳ Commit changes with incremental commits
8. ⏳ Update PROGRESS.md

---

## Notes

- **770 total instances** is a large number, but most follow predictable patterns
- **Bulk find-replace** is safe because we're always improving contrast (never reducing)
- **Dark mode** is the primary issue - light mode is mostly compliant
- **Testing after each batch** prevents cascading errors
- **Visual regression** is expected to be minimal (slightly lighter text)
