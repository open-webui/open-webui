# Stale Code Analysis - Moderation Scenario

## Summary

Analysis of the moderation scenario codebase to identify stale/unused code related to highlighting, reflecting, and deciding functionality.

## Flow Architecture Issue

**Current Behavior**: After Step 3 (Decide), **both "Accept" and "Moderate" decisions navigate to the moderation panel** (see `saveStep3Decision()` line 2169-2175).

**Code Location**: `src/routes/(app)/moderation-scenario/+page.svelte` line 2169-2175
```typescript
// Navigate to moderation panel (both accept and moderate go here)
if (decision !== 'not_applicable') {
    moderationPanelVisible = true;
    moderationPanelExpanded = false;
    expandedGroups.clear();
    showInitialDecisionPane = false;
}
```

**Conflict**: Line 1519 sets `moderationPanelVisible` based on conditions including `!acceptedOriginal`, which conflicts with the above logic that shows the panel for both accept and moderate.

## Stale Code Identified

### 1. `startModerating()` Function
- **Location**: Line 1977
- **Status**: DEPRECATED, never called
- **Comment**: "This function is no longer used in the new unified flow"
- **Action**: Can be removed

### 2. `finishHighlighting()` Function
- **Location**: Line 1990
- **Status**: Never called
- **Reason**: Highlighting now handled in Step 1 of unified flow
- **Action**: Can be removed

### 3. `submitReflection()` Function
- **Location**: Line 1999
- **Status**: Never called
- **Reason**: Reflection now handled in Step 2 of unified flow
- **Action**: Can be removed

### 4. `showReflectionModal` Variable
- **Location**: Line 1132
- **Status**: Always set to `false`, never used in UI
- **Comments**: Multiple comments say "No longer using separate modal"
- **Action**: Can be removed (variable and all assignments)

### 5. `highlightingMode` Variable
- **Location**: Line 1128
- **Status**: Set in multiple places but may not be actively used
- **Usage**: Only set to `false` in various reset functions
- **Action**: Verify if actually used in UI conditionals before removing

### 6. `satisfiedWithOriginalFromPanel()` Function
- **Location**: Line 2208
- **Status**: Defined but not found to be called
- **Action**: Verify if used in UI before removing

## Code Locations to Review

### Functions Never Called:
1. `startModerating()` - line 1977
2. `finishHighlighting()` - line 1990
3. `submitReflection()` - line 1999
4. `satisfiedWithOriginalFromPanel()` - line 2208 (verify)

### Variables Always False/Unused:
1. `showReflectionModal` - line 1132 (always false, never in UI conditionals)

### Potentially Unused:
1. `highlightingMode` - line 1128 (verify actual usage)

## Logic Conflicts

### Moderation Panel Visibility Conflict

**Location 1** (line 1519):
```typescript
moderationPanelVisible = confirmedVersionIndex === null && hasInitialDecision && !acceptedOriginal && !markedNotApplicable && step3Completed;
```

**Location 2** (line 2171):
```typescript
// Navigate to moderation panel (both accept and moderate go here)
if (decision !== 'not_applicable') {
    moderationPanelVisible = true;
    ...
}
```

**Issue**: Location 1 would hide the panel if `acceptedOriginal` is true, but Location 2 shows it for both accept and moderate. The reactive statement at line 1519 may override the explicit setting at line 2171.

## Recommendations

1. **Remove confirmed stale code**:
   - `startModerating()` function
   - `finishHighlighting()` function
   - `submitReflection()` function
   - `showReflectionModal` variable and all assignments

2. **Verify before removing**:
   - `highlightingMode` - check if used in UI conditionals
   - `satisfiedWithOriginalFromPanel()` - check if called from UI

3. **Resolve logic conflict**:
   - Clarify the intended behavior: Should "Accept" show the moderation panel or not?
   - Update line 1519 logic to match actual behavior (both accept and moderate show panel)
   - Or update line 2171 to only show panel for "moderate" decision

4. **Update documentation**:
   - Correct the flow architecture description to reflect that both accept and moderate navigate to moderation panel



