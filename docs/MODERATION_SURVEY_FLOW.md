# Moderation Survey Flow Documentation

## Overview

The moderation survey flow allows parents to review AI responses to child prompts and apply moderation strategies. This document outlines how questions are selected, how moderation decisions are made, and where data is saved.

## 1. Question/Scenario Selection Flow

### Scenario Sources

- **Personality-based scenarios**: Generated from child profile characteristics using `generateScenariosFromPersonalityData()` in `src/lib/data/personalityQuestions.ts` (primary source)
- **Custom scenario**: User-created scenario option (always appears last)

**Note**: Hardcoded default scenarios have been deprecated and are no longer used. The system now relies entirely on personality-based scenarios generated from child profile characteristics. The old hardcoded scenarios (previously at lines 80-92 in `moderation-scenario/+page.svelte`) have been commented out.

### Scenario Selection Process

**Backend Endpoint**: `GET /moderation/scenarios/available`

- Location: `backend/open_webui/routers/moderation_scenarios.py` (lines 168-221)
- Returns unseen scenario indices (0-11) for the current session
- Filters out scenarios already seen by the user for the given child_id
- Randomly shuffles available scenarios

**Frontend Flow** (`moderation-scenario/+page.svelte`):

1. On mount (lines 1962-2311):
   - Loads child profiles via `loadChildProfiles()` (line 500)
   - For Prolific users: Fetches available scenarios from backend (lines 2055-2109)
   - Generates personality-based scenarios via `generatePersonalityScenarios()` (line 546)
   - Applies attention check marker to one random scenario (line 317)
   - Ensures custom scenario is always last (line 301)

2. Scenario Package Persistence:
   - Scenarios are packaged and stored in localStorage with key `scenarioPkg_{childId}_{sessionNumber}`
   - Package includes: version, childId, sessionNumber, list of [question, response] pairs, createdAt
   - Once locked for a session, scenarios don't regenerate (prevents re-ordering)

3. Scenario List Building:
   - Base scenarios come exclusively from personality data (no fallback to hardcoded defaults)
   - Attention check is randomly injected into one response (line 317)
   - Custom scenario is appended at the end (line 301)

## 2. Moderation Decision Tree Flow

### Initial Decision Point

**Reflection Modal** (shown first):

- Location: `moderation-scenario/+page.svelte` (lines 1675-1687)
- User must provide reflection text before making decisions
- Modal shown when: `!hasInitialDecision && !scenarioReflection.trim()`
- Stored in `scenarioReflection` and saved to `session_metadata.reflection`

**Three Initial Decision Options**:

1. **Accept Original Response** (`acceptOriginalResponse()` - line 1611):
   - Sets: `hasInitialDecision = true`, `acceptedOriginal = true`, `confirmedVersionIndex = -1`
   - Saves session with `initial_decision: 'accept_original'`
   - No moderation strategies applied

2. **Start Moderating** (`startModerating()` - line 1656):
   - Sets: `hasInitialDecision = true`, `acceptedOriginal = false`
   - Enters highlighting mode first (`highlightingMode = true`)
   - User can highlight concerning text in prompt or response

3. **Mark Not Applicable** (`markNotApplicable()` - line 1706):
   - Sets: `hasInitialDecision = true`, `markedNotApplicable = true`
   - Saves session with `initial_decision: 'not_applicable'`
   - No moderation strategies applied

### Moderation Panel Flow (if "Start Moderating" chosen)

**Step 1: Highlighting Mode** (`finishHighlighting()` - line 1666):

- User highlights concerning text in original response or prompt
- Highlights stored in `highlightedTexts1` array
- Text selections saved to `/selections` endpoint (line 1025)

**Step 2: Strategy Selection**:

- User selects up to 3 moderation strategies from grouped options:
  - Refuse and Remove (4 options)
  - Investigate and Empathize (2 options)
  - Correct their Understanding (5 options)
  - Match their Age (1 option)
  - Defer to Support (2 options)
  - Attention Check (1 option - "I read the instructions")
  - Custom (user-defined instructions)
- Strategies stored in `selectedModerations` Set
- Custom instructions stored in `customInstructions` array

**Step 3: Apply Moderation** (`applySelectedModerations()` - line 1766):

- Calls `/moderation/apply` endpoint (backend: `backend/open_webui/routers/moderation.py`)
- Backend uses `multi_moderations_openai()` in `backend/open_webui/utils/moderation.py`
- Creates new version with:
  - `refactored_response`: AI-generated moderated response
  - `strategies`: Selected strategy names
  - `customInstructions`: Custom instruction texts
  - `highlightedTexts`: User-highlighted phrases
- Version stored in `versions` array with `currentVersionIndex` pointing to latest

**Step 4: Version Management**:

- User can navigate between versions (`navigateToVersion()` - line 1459)
- User can create multiple versions with different strategy combinations
- Each version saved immediately to database (line 1859)

**Step 5: Confirm Version** (`confirmCurrentVersion()` - line 1472):

- Sets `confirmedVersionIndex` to current version
- Hides moderation panel
- Marks scenario as completed

**Alternative: Satisfied with Original from Panel** (`satisfiedWithOriginalFromPanel()` - line 1696):

- Can accept original even after viewing moderated versions
- Calls `acceptOriginalResponse()` to save decision

## 3. Data Persistence Flow

### Frontend State Management

**Local Storage Keys** (child-specific):

- `moderationScenarioStates_{childId}`: Map of scenario index -> ScenarioState
- `moderationScenarioTimers_{childId}`: Map of scenario index -> time in seconds
- `moderationCurrentScenario_{childId}`: Current scenario index
- `scenarioPkg_{childId}_{sessionNumber}`: Canonical scenario package

**ScenarioState Interface** (line 871):

```typescript
{
  versions: ModerationVersion[],
  currentVersionIndex: number,
  confirmedVersionIndex: number | null,
  highlightedTexts1: string[],
  selectedModerations: Set<string>,
  customInstructions: Array<{id: string, text: string}>,
  showOriginal1: boolean,
  hasInitialDecision: boolean,
  acceptedOriginal: boolean,
  attentionCheckSelected: boolean,
  markedNotApplicable: boolean,
  customPrompt?: string,
  scenarioReflection: string
}
```

### Backend Database Schema

**Table**: `moderation_session`

- Location: `backend/open_webui/models/moderation.py` (lines 12-53)
- Key fields:
  - `scenario_index`: Which scenario (0-based)
  - `attempt_number`: Usually 1
  - `version_number`: Increments for each moderated version (0 = original decision)
  - `session_number`: Session identifier
  - `initial_decision`: 'accept_original' | 'moderate' | 'not_applicable'
  - `is_final_version`: Boolean marking final choice
  - `strategies`: JSON array of strategy names
  - `custom_instructions`: JSON array of custom instruction texts
  - `highlighted_texts`: JSON array of highlighted phrases
  - `refactored_response`: Final moderated response text
  - `session_metadata`: JSON object with reflection, decision timestamp, etc.

### Save Operations

**Immediate Saves** (via `saveModerationSession()`):

1. **Initial decision** (lines 1624-1653, 1719-1749):
   - When accepting original or marking not applicable
   - Saves with `version_number: 0`, `is_final_version: false`

2. **Each moderated version** (lines 1859-1889):
   - When `applySelectedModerations()` creates new version
   - Saves with incremented `version_number`
   - Includes all strategies, custom instructions, highlighted texts
   - `is_final_version: false` until finalized

3. **State persistence** (`saveCurrentScenarioState()` - line 1153):
   - Saves to localStorage on every state change
   - Reactive statement triggers on key state changes (line 2323)

**Finalization** (`finalizeModeration()` - line 1936):

- Endpoint: `POST /workflow/moderation/finalize`
- Location: `backend/open_webui/routers/workflow.py` (lines 382-435)
- Called when user completes all scenarios and proceeds to exit survey
- Groups sessions by (child_id, scenario_index, attempt_number, session_number)
- Marks the latest created row as `is_final_version: true` for each scenario
- Clears `is_final_version` on all other versions for that scenario

### Session Activity Tracking

**Endpoint**: `POST /moderation/session-activity`

- Location: `backend/open_webui/routers/moderation_scenarios.py` (lines 96-115)
- Tracks active time spent on moderation session
- Syncs every 30 seconds (line 239)
- Uses idle threshold of 60 seconds (line 207)

## 4. Attention Check Flow

**Detection**:

- One scenario randomly selected to have attention check marker appended to response
- Marker: `<!--ATTN-CHECK-->` (line 96)
- Suffix includes instruction: "Please moderate this question. Follow these steps: 1) Step 1: Click \"Continue\" (you can skip highlighting). 2) Step 2: In the \"I feel...\" field, enter \"test\" and in the \"because...\" field, enter \"test\", then click \"Continue\". 3) Step 3: Choose \"Moderate\" (not \"Accept\"). 4) Then select 'I read the instructions' from the \"Attention Check\" dropdown before generating a moderated version."

**Behavior**:

- `isAttentionCheckScenario` reactive variable (line 911)
- When user selects "I read the instructions" from the Attention Check dropdown (line 1773):
  - Immediately saves attention check as passed to backend (`attention_check_passed: true`)
  - Sets completion flags: `hasInitialDecision = true`, `acceptedOriginal = true`, `step3Completed = true`
  - Closes panels: `moderationPanelVisible = false`, `showInitialDecisionPane = false`
  - Saves state to localStorage for persistence
  - Automatically navigates to next scenario after 1 second delay
  - Shows success message: "✓ Passed attention check! Moving to next scenario..."
- Tracks: `attention_check_selected`, `attention_check_passed` in database
- State persists when navigating back - scenario shows as completed

## 5. Custom Scenario Flow

**Generation** (`generateCustomScenarioResponse()` - line 758):

- User enters custom prompt
- Calls moderation API with empty strategies to generate baseline response
- Response becomes the "original_response" for moderation
- Custom prompt stored in `scenarioState.customPrompt`
- Treated like any other scenario after generation

## Key Files Reference

- **Frontend Main Component**: `src/routes/(app)/moderation-scenario/+page.svelte`
- **Backend Session Router**: `backend/open_webui/routers/moderation_scenarios.py`
- **Backend Moderation Router**: `backend/open_webui/routers/moderation.py`
- **Moderation Utils**: `backend/open_webui/utils/moderation.py`
- **Database Models**: `backend/open_webui/models/moderation.py`
- **Workflow Router**: `backend/open_webui/routers/workflow.py` (finalization)
- **API Client**: `src/lib/apis/moderation/index.ts`

## Flow Diagram

```
User loads moderation page
    ↓
Load child profiles
    ↓
Generate/fetch scenarios (personality-based or default)
    ↓
Apply attention check to random scenario
    ↓
Add custom scenario at end
    ↓
Lock scenario package for session
    ↓
For each scenario:
    ↓
Show reflection modal (if not provided)
    ↓
User makes initial decision:
    ├─ Accept Original → Save decision → Mark complete
    ├─ Mark Not Applicable → Save decision → Mark complete
    └─ Start Moderating → Enter highlighting mode
            ↓
        User highlights concerning text (optional)
            ↓
        User selects moderation strategies (up to 3)
            ↓
        Apply moderation → Generate moderated version
            ↓
        Save version to database
            ↓
        User can create more versions or confirm current
            ↓
        Confirm version → Mark scenario complete
    ↓
All scenarios completed?
    ↓
Finalize moderation (mark latest versions as final)
    ↓
Proceed to exit survey
```

