# Implementation Plan: Survey Workflow Updates

## Overview

This plan covers updates to attention check flow, child profile, scenario review, and exit survey based on user requirements.

---

## 1. Attention Check Flow Update

### Current State

- Attention check has 3-step instructions embedded in response text
- Flow uses existing moderation steps but with special validation

### Required Changes

#### 1.1 Frontend Changes (`src/routes/(app)/moderation-scenario/+page.svelte`)

**IMPORTANT: Attention checks should NOT block progress. Users can proceed regardless of completion. The check only tracks whether they passed.**

**Step 1: Highlight Tracking (Non-blocking)**

- Track if user highlighted anything in the response for attention checks
- Do NOT block progress if no highlights - allow user to continue
- Update `step1Completed` logic to check highlights for attention checks (for tracking only)
- Store highlight status in state: `attentionCheckStep1Passed: boolean`

**Step 2: "attention check" Text Tracking (Non-blocking)**

- Track if `concernReason` contains "attention check" (case-insensitive)
- Do NOT block progress if text is missing - allow user to continue
- Update `step2Completed` logic for attention checks (for tracking only)
- Store text status in state: `attentionCheckStep2Passed: boolean`

**Step 3: "I read the instructions" Selection Tracking (Non-blocking)**

- Ensure "I read the instructions" option exists in Attention Check dropdown
- Track if this selection is made for attention checks
- Do NOT block progress if not selected - allow user to continue
- Update `step3Completed` logic for attention checks (for tracking only)
- Store selection status in state: `attentionCheckStep3Passed: boolean`

**Overall Attention Check Pass/Fail Logic:**

- Calculate `attentionCheckPassed = attentionCheckStep1Passed && attentionCheckStep2Passed && attentionCheckStep3Passed`
- This is for tracking/analytics only - does NOT affect user's ability to proceed
- Users can complete the scenario and move to next scenario even if attention check is failed

**Files to Modify:**

- `src/routes/(app)/moderation-scenario/+page.svelte`
  - Update Step 1 completion logic (around line 1060-1200) - track highlights but don't block
  - Update Step 2 completion logic (around line 1200-1400) - track text but don't block
  - Update Step 3 completion logic (around line 1400-1600) - track selection but don't block
  - Remove any blocking validation for attention checks
  - Update `isScenarioCompleted` function - attention checks complete when user proceeds (not based on pass/fail)
  - Add tracking fields to `ScenarioState` interface: `attentionCheckStep1Passed`, `attentionCheckStep2Passed`, `attentionCheckStep3Passed`

#### 1.2 Backend Changes

**Validation Endpoint** (if needed)

- Check if backend needs validation endpoint for attention check completion
- File: `backend/open_webui/routers/moderation_scenarios.py`
- May need to add validation logic when saving moderation sessions

**Database Schema** (if needed)

- Check if attention check completion needs to be tracked separately
- May need to add `attention_check_passed` flag to moderation sessions

#### 1.3 Update Instructions Text

- Update `ATTENTION_CHECK_SUFFIX` constant to reflect new 3-step flow
- File: `src/routes/(app)/moderation-scenario/+page.svelte` (around line 140)

---

## 2. Child Profile Updates

### 2.1 Add Message to Child Profile Page

**File:** `src/routes/(app)/kids/profile/+page.svelte` or `src/lib/components/profile/ChildProfileForm.svelte`

**Change:**

- Add instructional message at top of form: "Consider one kid you are thinking about - consider the oldest etc."
- Place before the form fields, styled as an info/instructional banner

### 2.2 Check MVP for Child Creation in Chat Parent Version

**Tasks:**

1. Search for child profile creation in chat/parent interface
2. Identify MVP fields used in chat version
3. Compare with current quiz child profile fields
4. Document which fields to keep in quiz vs move to exit survey

**Files to Review:**

- Search for child profile creation in parent/chat routes
- `src/lib/components/profile/ChildProfileForm.svelte`
- `src/lib/apis/child-profiles/index.ts`
- Backend models: `backend/open_webui/models/child_profiles.py`

**Expected MVP Fields (to keep in quiz):**

- Basic identifying info (name, age, etc.)
- Minimal fields needed for scenario assignment

### 2.3 Move Remaining Fields to Exit Survey

**Tasks:**

1. Identify fields currently in child profile that should move to exit survey
2. Update child profile form to only include MVP fields
3. Add moved fields to exit survey form
4. Update backend API to handle field migration
5. Update data models if needed

**Files to Modify:**

- `src/lib/components/profile/ChildProfileForm.svelte` - Remove non-MVP fields
- `src/routes/(app)/exit-survey/+page.svelte` - Add child profile fields
- `backend/open_webui/models/child_profiles.py` - Update schema if needed
- `backend/open_webui/models/exit_quiz.py` - Add fields to exit quiz schema

---

## 3. Scenario Review - Likert Scale Concern Rating

### Current State

- Step 2 has "Explain why this content concerns you" field
- Concern level is tracked but may not be displayed in the right place

### Required Changes

**File:** `src/routes/(app)/moderation-scenario/+page.svelte`

**Changes:**

1. Add Likert scale rating BEFORE "Explain why" field in Step 2 panel
2. Question: "To what extent, if any, are you concerned about this interaction?"
3. Options (radio buttons):
   - Not concerned at all
   - Somewhat unconcerned
   - Neutral
   - Somewhat concerned
   - Concerned

**Implementation:**

- Add new state variable: `concernRating: string | null = null` (or reuse `concernLevel` if it's the same)
- Add Likert scale UI component in Step 2 panel (before concernReason textarea)
- Update validation to require concern rating before proceeding
- Store in `ScenarioState` and persist to backend
- Update `saveCurrentScenarioState` to include concern rating
- Update `loadScenario` to restore concern rating

**Location in Code:**

- Find Step 2 panel rendering (around line 2000-2500)
- Add Likert scale before concernReason textarea
- Update Step 2 completion logic

---

## 4. Exit Survey - Parenting Style Multi-Select

### Current State

- Parenting style is single-select (radio buttons)
- Options: A, B, C, D, E, prefer-not-to-answer

### Required Changes

**File:** `src/routes/(app)/exit-survey/+page.svelte`

**Changes:**

1. Change `parentingStyle` from string to array: `parentingStyle: []`
2. Replace radio buttons with checkboxes (multi-select)
3. Update validation to allow multiple selections
4. Update backend API to handle array instead of string
5. Update `applyAnswersToForm` to handle array
6. Update display in summary section to show multiple selections

**Implementation Steps:**

1. Change `surveyResponses.parentingStyle` from `''` to `[]`
2. Replace `bind:group={surveyResponses.parentingStyle}` with `bind:group={surveyResponses.parentingStyle}` (works with arrays for checkboxes)
3. Change `<input type="radio">` to `<input type="checkbox">`
4. Update validation: `if (!surveyResponses.parentingStyle || surveyResponses.parentingStyle.length === 0)`
5. Update backend model if needed: `backend/open_webui/models/exit_quiz.py`
6. Update API serialization to handle array

**Files to Modify:**

- `src/routes/(app)/exit-survey/+page.svelte` (around line 460-545)
- `backend/open_webui/models/exit_quiz.py` (if schema change needed)
- `backend/open_webui/routers/exit_quiz.py` (if API change needed)

---

## Implementation Order

1. **Attention Check Flow** (highest priority - affects validation)
   - Update instructions text
   - Update Step 1 validation (highlights required)
   - Update Step 2 validation ("attention check" text required)
   - Update Step 3 validation ("I read the instructions" required)
   - Test validation flow

2. **Scenario Review Likert Scale** (medium priority)
   - Add concern rating Likert scale
   - Update state management
   - Update persistence

3. **Child Profile Updates** (medium priority)
   - Add instructional message
   - Research MVP fields in chat version
   - Update child profile form (remove non-MVP fields)
   - Move fields to exit survey

4. **Exit Survey Parenting Style** (lower priority - UI change)
   - Change to multi-select
   - Update backend if needed

---

## Testing Checklist

### Attention Check

- [ ] Step 1: User can proceed with or without highlighting (tracking only)
- [ ] Step 2: User can proceed with or without "attention check" text (tracking only)
- [ ] Step 3: User can proceed with or without selecting "I read the instructions" (tracking only)
- [ ] Attention check pass/fail is calculated but does NOT block progress
- [ ] Users can complete scenario and move to next scenario regardless of attention check result
- [ ] Pass/fail status is stored for analytics but doesn't affect workflow

### Child Profile

- [ ] Instructional message displays at top
- [ ] Only MVP fields shown in quiz child profile
- [ ] Moved fields appear in exit survey
- [ ] Data persists correctly after migration

### Scenario Review

- [ ] Likert scale appears before "Explain why" field
- [ ] Concern rating is required before proceeding
- [ ] Rating persists across page reloads
- [ ] Rating is saved to backend

### Exit Survey

- [ ] Parenting style allows multiple selections
- [ ] Multiple selections are saved correctly
- [ ] Summary shows all selected options
- [ ] Backend handles array format

---

## Notes

- **CRITICAL: Attention checks are non-blocking** - users can proceed regardless of whether they follow the instructions. The check only tracks pass/fail for analytics.
- All changes should maintain backward compatibility where possible
- Consider data migration for existing users if schema changes are needed
- Update Cypress tests after implementation
- Ensure all validation messages are clear and user-friendly
- Regular scenario flow should be completely unaffected by attention check changes
