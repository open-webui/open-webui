# Commit Message: Consolidate child selection state to settings store (single source of truth)

## Problem

Child selection was not persisting across page refresh and state was getting out of sync because there were **three separate sources of truth**:

1. `user.settings.ui.selectedChildId` (in user store) - but user store doesn't include settings data
2. `localStorage.selectedChildId` - separate localStorage key
3. `localStorage.selectedChildForQuestions` - yet another localStorage key
4. `settings.selectedChildId` (in settings store) - the actual source loaded from backend

The `getCurrentChildId()` function was reading from `user.settings.ui.selectedChildId`, but on page refresh, the user store (populated from `/auths/`) doesn't include settings. The settings store (populated from `/users/user/settings`) was the correct source, causing `getCurrentChildId()` to return `null` and defaulting to the first child.

## Root Cause

The architecture had two stores with overlapping concerns:
- `user` store: populated from `/auths/` endpoint - contains auth/identity data only (id, token, role, permissions)
- `settings` store: populated from `/users/user/settings` endpoint - contains UI preferences (theme, selectedChildId, etc.)

The code was incorrectly reading UI settings from the `user` store instead of the `settings` store.

## Solution: Establish Single Source of Truth Rule

**Rule established:**
- `user` store = auth/identity only (id, token, role, permissions)
- `settings` store = all UI preferences (theme, selectedChildId, etc.)
- **Never read/write UI settings from `user.settings` or `localStorage.selectedChildId`**

## Changes Made

### 1. `src/lib/services/childProfileSync.ts`

**Updated `getCurrentChildId()`:**
- Changed from reading `user.settings.ui.selectedChildId` 
- Now reads from `settings.selectedChildId` (the actual backend source)

**Updated `setCurrentChildId()`:**
- Still calls `updateUserSettings()` API for backend persistence
- Changed local store update from `user.update()` to `settings.update()`
- Now updates the `settings` store which `getCurrentChildId()` reads from

**Added import:** `settings` store from `$lib/stores`

### 2. `src/lib/components/layout/Sidebar.svelte`

**Updated reactive dependency (line 96):**
- Changed from: `const _ = $user?.settings?.ui?.selectedChildId;`
- Changed to: `const _ = $settings?.selectedChildId;`
- Ensures Sidebar re-renders when settings store updates

### 3. `src/routes/(app)/kids/profile/+page.svelte`

**Updated `loadChildProfile()`:**
- Now sets both `selectedChildIndex` and `childSelectedForQuestions` from the same backend source (`getCurrentChildId()`)
- Removed the `-1` reset that was causing the green indicator to not show

**Removed localStorage reads:**
- Removed `localStorage.getItem('selectedChildForQuestions')` block from `onMount` that was overriding the backend value

**Removed localStorage writes:**
- Removed all `localStorage.setItem('selectedChildForQuestions', ...)` calls (3 locations)
- State now flows: backend → settings store → UI

**Updated `waitForUser()` function:**
- Relaxed condition to only require `userData.id` instead of `userData.settings`
- Prevents blocking when settings haven't loaded yet (they load separately)

### 4. `src/routes/(app)/exit-survey/+page.svelte`

**Updated `resolveChildId()` function:**
- Removed dependency on `localStorage.getItem('selectedChildForQuestions')`
- Now uses `getCurrentChildId()` as primary source (which reads from settings store)
- Falls back to first available profile if no selection

**Simplified submit handler:**
- Removed duplicate localStorage logic
- Now reuses the consolidated `resolveChildId()` function

### 5. `src/routes/auth/+page.svelte`

**When creating new child during Prolific auth (line 249):**
- Changed from: `localStorage.setItem('selectedChildId', authResponse.new_child_id)`
- Changed to: `await childProfileSync.setCurrentChildId(authResponse.new_child_id)`
- Now properly persists to backend and updates settings store

**Removed localStorage cleanup:**
- Removed `localStorage.removeItem('selectedChildId')` calls (2 locations)
- No longer needed since we're not using localStorage for this

**Added import:** `childProfileSync` service

### 6. `src/lib/components/layout/Sidebar/UserMenu.svelte`

**When clearing child state on study restart (line 72):**
- Changed from: `localStorage.getItem('selectedChildId')`
- Changed to: `childProfileSync.getCurrentChildId()`
- Uses the same source as everywhere else

**Removed localStorage cleanup:**
- Removed `localStorage.removeItem('selectedChildId')` call
- Already handled by `setCurrentChildId(null)` call on line 84

### 7. `src/routes/(app)/moderation-scenario/+page.svelte`

**Fixed fallback for child_id in selections API (line 1209):**
- Changed from: `child_id: localStorage.getItem('selectedChildId') || 'unknown'`
- Changed to: `child_id: selectedChildId || 'unknown'`
- Uses the local `selectedChildId` variable (populated from `getCurrentChildId()`)

## Impact

- ✅ Child selection now persists across page refresh
- ✅ Single source of truth eliminates state sync bugs
- ✅ Green indicator and blue halo always show the same child
- ✅ No more localStorage usage for selectedChildId (consolidated to settings store)
- ✅ Backend sync works correctly via `updateUserSettings()` API

## Files Changed

- `src/lib/services/childProfileSync.ts` (core service - get/set methods)
- `src/lib/components/layout/Sidebar.svelte` (reactive dependency)
- `src/routes/(app)/kids/profile/+page.svelte` (loadChildProfile, removed localStorage)
- `src/routes/(app)/exit-survey/+page.svelte` (resolveChildId consolidation)
- `src/routes/auth/+page.svelte` (Prolific auth flow)
- `src/lib/components/layout/Sidebar/UserMenu.svelte` (study restart)
- `src/routes/(app)/moderation-scenario/+page.svelte` (API fallback)

