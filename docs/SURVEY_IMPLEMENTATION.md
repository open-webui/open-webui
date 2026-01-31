# Webapp Survey Implementation Guide

## Overview

The webapp has two survey types: **Initial Survey** (pre-assignment) and **Exit Survey** (post-assignment, Task 3). Both are integrated into the assignment workflow and track completion state.

## Survey Types

### 1. Initial Survey (`/initial-survey`)

**Purpose:** Pre-assignment demographic and experience survey  
**Location:** `src/routes/(app)/initial-survey/+page.svelte`  
**Endpoint:** `/api/v1/initial-surveys` (POST)  
**Storage:** Backend API (implementation may need verification)  
**Completion Tracking:** LocalStorage flag `initialSurveyCompleted`

**Questions:**

- Experience with AI systems and chatbots (text)
- General parenting approach (text)
- Content moderation experience (text)
- Expectations for assignment (text)
- Concerns about AI systems (text)
- Technology comfort level (radio: very-comfortable to very-uncomfortable)

**Key Features:**

- Auto-redirects if already completed
- Navigation to assignment instructions after completion

---

### 2. Exit Survey (`/exit-survey`)

**Purpose:** Post-assignment demographic and experience survey (Task 3)  
**Location:** `src/routes/(app)/exit-survey/+page.svelte`  
**Backend:** Exit Quiz system  
**API Endpoint:** `/api/v1/exit-quiz` (POST)  
**Database Table:** `exit_quiz_response`

**Questions (structured fields):**

- `parentGender`: Gender selection
- `parentAge`: Age range selection
- `areaOfResidency`: Geographic location
- `parentEducation`: Education level
- `parentEthnicity`: Multi-select ethnicity (array)
- `genaiFamiliarity`: Familiarity with LLMs
- `genaiUsageFrequency`: Personal AI use frequency
- `parentingStyle`: Parenting style selection

**Key Features:**

- **Draft Auto-save:** Debounced (500ms) localStorage draft saving per user/child
- **Child Profile Integration:** Requires active child profile, resolves via `childProfileSync`
- **Completion Tracking:** Per-user, per-child completion flags in localStorage
- **Workflow Integration:** Sets `assignmentStep=4`, triggers workflow update events
- **Confirmation Modal:** Shows completion confirmation before proceeding

---

## Database Schema

### Exit Quiz Response Table (`exit_quiz_response`)

**Important:** The `question_key` column was originally NOT NULL but has been made nullable (migration `r44s55t66u77`). This fixes the submission error where the code doesn't provide a `question_key` value.

**Columns:**

- `id` (String, PK)
- `user_id` (String, NOT NULL)
- `child_id` (String, NOT NULL)
- `question_key` (String, **NULLABLE** - see note above)
- `answers` (JSON) - Contains all survey responses in structured format
- `score` (JSON, nullable)
- `meta` (JSON, nullable) - Typically contains `{page: 'exit-survey'}`
- `attempt_number` (Integer, default 1)
- `is_current` (Boolean, default True)
- `created_at` (BigInteger)
- `updated_at` (BigInteger)

**Indexes:**

- `idx_exit_quiz_user_id` on `user_id`
- `idx_exit_quiz_child_id` on `child_id`
- `idx_exit_quiz_created_at` on `created_at`
- `idx_exit_quiz_attempt` on `(user_id, child_id, attempt_number)`
- `idx_exit_quiz_user_current` on `(user_id, is_current)`

---

## API Endpoints

### Exit Quiz API (`/api/v1/exit-quiz`)

**Router:** `backend/open_webui/routers/exit_quiz.py`  
**Model:** `backend/open_webui/models/exit_quiz.py`

**Endpoints:**

- `POST /exit-quiz` - Create new exit quiz response
- `GET /exit-quiz?child_id={id}` - List responses (optional child filter)
- `GET /exit-quiz/{id}` - Get specific response
- `PUT /exit-quiz/{id}` - Update response
- `DELETE /exit-quiz/{id}` - Delete response

**Request Format:**

```json
{
	"child_id": "uuid",
	"answers": {
		"parentGender": "...",
		"parentAge": "..."
		// ... other fields
	},
	"meta": {
		"page": "exit-survey"
	}
}
```

---

## Workflow Integration

### Assignment Steps

The exit survey is **Task 3** in the assignment workflow:

1. Task 1: Child Profile Creation (`/kids/profile`)
2. Task 2: Moderation Scenarios (`/moderation-scenario`)
3. Task 3: Exit Survey (`/exit-survey`)
4. Task 4: Completion Page (`/completion`)

### Completion State Tracking

**Workflow API:** `backend/open_webui/routers/workflow.py`

The workflow system checks for exit survey completion:

- Looks for latest current exit quiz response per user
- Sets `exit_survey_completed: true` if found
- Routes users to `/exit-survey` if not completed

**LocalStorage Keys:**

- `assignmentStep`: Current step (3 = exit survey)
- `assignmentCompleted`: Overall completion flag
- `exitSurveyCompleted:{userId}:{childId}`: Per-user/child completion
- `exitSurveyDraft:{userId}:{childId}`: Draft storage

---

## Frontend Implementation Details

### Exit Survey Component

**File:** `src/routes/(app)/exit-survey/+page.svelte`

**Key Functions:**

- `submitSurvey()`: Validates fields, resolves child_id, calls API, updates workflow state
- `resolveChildId()`: Multi-tier fallback to find active child profile
- `saveDraft()`: Debounced auto-save to localStorage
- Draft loading on mount

**Validation:**

- All fields are required (shows toast errors for missing fields)
- Ethnicity must have at least one selection
- Requires valid child profile (error if none found)

**Draft System:**

- Auto-saves on any field change (debounced 500ms)
- Restores draft on page load
- Clears draft on successful submission

---

## Important Gotchas & Issues Fixed

### 1. Question Key Nullability (Fixed)

**Issue:** Database schema had `question_key` as NOT NULL, but code doesn't provide it.  
**Fix:** Migration `r44s55t66u77` made `question_key` nullable.  
**Impact:** Must run this migration on production database before exit survey submissions will work.

### 2. Child Profile Requirement

Exit survey requires an active child profile. If none exists, shows error and prevents submission. The `resolveChildId()` function has multiple fallback strategies.

### 3. Multiple Attempt Support

Database supports `attempt_number` tracking, but current implementation always creates with `attempt_number=1`. Future feature for retake capability.

### 4. LocalStorage vs Backend State

Completion is tracked both in localStorage (for UI state) and backend (for data persistence). Workflow API reads from backend, so localStorage flags are mainly for UI responsiveness.

---

## Testing Checklist

- [ ] Submit exit survey with all fields filled
- [ ] Submit with missing fields (should show validation errors)
- [ ] Auto-save draft functionality (check localStorage)
- [ ] Draft restoration on page reload
- [ ] Completion modal appears after submission
- [ ] Workflow updates to step 4 after submission
- [ ] Verify data persists in `exit_quiz_response` table
- [ ] Test with no child profile (should error gracefully)
- [ ] Verify migration `r44s55t66u77` is applied (question_key nullable)

---

## Related Files

**Frontend:**

- `src/routes/(app)/exit-survey/+page.svelte` - Exit survey component
- `src/routes/(app)/initial-survey/+page.svelte` - Initial survey component
- `src/lib/apis/exit-quiz/index.ts` - Exit quiz API client

**Backend:**

- `backend/open_webui/models/exit_quiz.py` - Database model
- `backend/open_webui/routers/exit_quiz.py` - API routes
- `backend/open_webui/routers/workflow.py` - Workflow state management
- `backend/open_webui/migrations/versions/r44s55t66u77_*.py` - Question key nullable fix

**Services:**

- `src/lib/services/childProfileSync.ts` - Child profile sync service (used for child_id resolution)
