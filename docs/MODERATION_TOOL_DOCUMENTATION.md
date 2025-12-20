# Moderation Tool Documentation

## Overview

This document provides a comprehensive guide to the moderation tool workflow, including all functions, state management, UI interactions, and data persistence. The moderation tool allows parents to review AI responses to child prompts and apply moderation strategies to refactor responses according to their preferences.

## 1. Moderation Flow Architecture

The moderation system follows a structured workflow:

### Initial Decision Flow (3-Step Process)

1. **Step 1 - Highlight**: User highlights concerning text in the original response (optional)
2. **Step 2 - Reflect**: User enters reflection using "I feel..." and "because..." template
3. **Step 3 - Decide**: User chooses to either:
   - **Accept**: Accept the original response (still proceeds to moderation panel)
   - **Moderate**: Enter moderation to create a modified version
   - **Not Applicable**: Mark scenario as not applicable (skips moderation panel)

**Note**: Both "Accept" and "Moderate" decisions navigate to the moderation panel, allowing users to optionally create moderated versions even after accepting the original.

### Moderation Panel

After choosing to moderate, users can:
- Select up to 3 moderation strategies (standard + custom combined)
- Add custom instructions via text input
- Apply moderation to generate a new version

### Version Management

- Users can create multiple moderated versions with different strategy combinations
- Navigate between versions using previous/next arrows
- Toggle between viewing original and moderated versions
- Each version is saved immediately to the backend

### Final Decision

- Users can confirm a version as their final choice
- Users can create additional versions if not satisfied
- Once confirmed, the version is marked as final in the database

## 2. Core Functions and Their Purposes

### Frontend Functions (`src/routes/(app)/moderation-scenario/+page.svelte`)

#### `applySelectedModerations()` (line ~2290)
- **Purpose**: Calls backend API to generate a moderated response
- **Process**:
  1. Separates standard strategies from custom instruction IDs
  2. Calls `applyModeration()` API function with all parameters
  3. Creates new `ModerationVersion` object from response
  4. Adds version to `versions[]` array
  5. Updates `currentVersionIndex` to new version
  6. Saves version to backend via `saveModerationSession()`
- **Key Parameters**:
  - `moderationTypes`: Standard strategy names
  - `customInstructions`: Custom instruction texts
  - `originalResponse1`: Original response (for refactoring)
  - `highlightedTexts1`: User-highlighted phrases
  - `childAge`: Child's age (for age-appropriate tailoring)

#### `navigateToVersion(direction: 'prev' | 'next')` (line ~1711)
- **Purpose**: Navigate between version indices
- **Behavior**: 
  - Prevents navigation if version is confirmed
  - Updates `currentVersionIndex` based on direction
  - Does not auto-populate moderation panel (keeps it clear)

#### `confirmCurrentVersion()` (line ~1724)
- **Purpose**: Mark a version as final choice
- **Behavior**:
  - Sets `confirmedVersionIndex` to current version
  - Hides moderation panel
  - Saves state to localStorage
  - Can be called again to unconfirm (allows editing)

#### `toggleModerationSelection(option: string)` (line ~1767)
- **Purpose**: Select/deselect moderation strategies
- **Special Handling**:
  - Custom option: Toggles custom input field
  - Attention check: Special handling for attention check scenarios
  - Enforces limit of 3 strategies total (standard + custom)

#### `getCurrentVersionResponse()` (line ~1746)
- **Purpose**: Get response text for current version
- **Returns**: Current version response or original if no version selected

#### `acceptOriginalResponse()` (line ~1932)
- **Purpose**: Accept original response (called from moderation panel, not Step 3)
- **Behavior**:
  - Sets `hasInitialDecision = true`
  - Sets `acceptedOriginal = true`
  - Sets `confirmedVersionIndex = -1`
  - Hides moderation panel
  - Saves decision to backend with `initial_decision: 'accept_original'`
- **Note**: This is different from Step 3 "Accept" button, which calls `saveStep3Decision('accept_original')` and still shows the moderation panel

#### `startModerating()` (line ~1977)
- **Status**: STALE - Commented out, no longer used
- **Note**: DEPRECATED - No longer used in unified flow (highlighting now in Step 1)

#### `loadScenario(index: number, forceReload: boolean)` (line ~1406)
- **Purpose**: Load scenario state from localStorage
- **Process**:
  1. Saves current state before switching (unless forcing reload)
  2. Loads saved state from `scenarioStates` Map
  3. Restores all state variables (versions, highlights, decisions, etc.)
  4. Handles custom scenario special cases
  5. Starts timer for the scenario

#### `saveCurrentScenarioState()` (line ~1354)
- **Purpose**: Persist state to localStorage
- **Saves**: All state variables to `scenarioStates` Map
- **Triggered**: On every state change (reactive statement at line ~2323)

### Backend Functions

#### `apply_moderation()` (`backend/open_webui/routers/moderation.py`)
- **Purpose**: API endpoint for applying moderation
- **Endpoint**: `POST /moderation/apply`
- **Process**:
  1. Validates request
  2. Gets OpenAI API key from config or environment
  3. Calls `multi_moderations_openai()` utility function
  4. Returns moderation result

#### `multi_moderations_openai()` (`backend/open_webui/utils/moderation.py`)
- **Purpose**: Core moderation logic
- **Modes**:
  - **Refactoring Mode**: When `original_response` provided, rewrites existing response
  - **Generation Mode**: When `original_response` is None, generates new response
- **Process**:
  1. Validates and deduplicates moderation types
  2. Builds combined instruction list from all strategies
  3. Customizes "Tailor to Age Group" if child_age provided
  4. Constructs system prompt based on mode
  5. Calls OpenAI API with model `gpt-5.2`
  6. Parses JSON response
  7. Returns refactored response and system prompt rule

## 3. State Management

### Key State Variables

#### Version Management
- **`versions[]`**: Array of `ModerationVersion` objects
  - Each version contains:
    - `response`: The moderated response text
    - `strategies`: Array of standard strategy names
    - `customInstructions`: Array of custom instruction objects `{id, text}`
    - `highlightedTexts`: Array of highlighted phrases
    - `moderationResult`: Full API response object

- **`currentVersionIndex`**: Currently displayed version index
  - `-1`: Viewing original response
  - `0+`: Viewing moderated version at that index

- **`confirmedVersionIndex`**: Index of confirmed version
  - `null`: No version confirmed yet
  - `number`: Index of confirmed version

#### Display State
- **`showOriginal1`**: Boolean toggle for viewing original vs moderated
  - `true`: Show original response with highlights
  - `false`: Show current moderated version

#### User Input State
- **`highlightedTexts1[]`**: Array of text selections from user
  - Stored as strings (the actual selected text)
  - Used to highlight concerns in original response

- **`selectedModerations`**: Set of selected strategy names
  - Contains standard strategy names and custom instruction IDs
  - Maximum 3 selections allowed

- **`customInstructions[]`**: Array of custom instruction objects
  - Format: `{id: string, text: string}`
  - IDs are prefixed with `custom_` and timestamp

#### Decision State
- **`hasInitialDecision`**: Whether user completed initial 3-step flow
- **`acceptedOriginal`**: Whether user accepted original response
- **`markedNotApplicable`**: Whether scenario was marked as not applicable
- **`attentionCheckSelected`**: Whether attention check was selected

#### Initial Decision Flow State
- **`initialDecisionStep`**: Current step (1, 2, or 3)
- **`step1Completed`**: Whether highlighting step completed
- **`step2Completed`**: Whether reflection step completed
- **`step3Completed`**: Whether decision step completed
- **`reflectionFeeling`**: "I feel..." text
- **`reflectionReason`**: "because..." text
- **`initialDecisionChoice`**: User's choice ('accept_original' | 'moderate' | null)
- **`showInitialDecisionPane`**: Whether to show the 3-step pane

### localStorage Persistence

#### Child-Specific Keys
- **`moderationScenarioStates_{childId}`**: Map of scenario index → ScenarioState
  - Persists all state for each scenario
  - Restored when loading scenario

- **`moderationScenarioTimers_{childId}`**: Map of scenario index → time in seconds
  - Tracks time spent on each scenario

- **`moderationCurrentScenario_{childId}`**: Current scenario index
  - Persists which scenario user is viewing

- **`scenarioPkg_{childId}_{sessionNumber}`**: Canonical scenario package
  - Contains: version, childId, sessionNumber, list of [question, response] pairs, createdAt
  - Locked for session to prevent re-ordering

## 4. Moderation Strategy Selection

### Available Strategies (Grouped by Category)

#### Refuse and Remove (4 options)
1. **Refuse Response and Explain**: Decline to answer with child-friendly reason
2. **Remove Harmful Phrases**: Avoid or replace harmful wording
3. **Omit Unprompted Suggestions**: Only answer direct question, no extra tips
4. **Do Not Suggest Workarounds**: Avoid offering workarounds or loopholes

#### Investigate and Empathize (2 options)
1. **Clarify Child's Intent**: Ask gentle clarifying question first
2. **Emphasize Emotional Support**: Acknowledge feelings in warm, friendly tone

#### Correct their Understanding (5 options)
1. **Explain Problems in Prompt**: Gently explain why idea could be unsafe/problematic
2. **Emphasize Risk Awareness**: Briefly mention age-appropriate risks
3. **Redirect with Alternatives**: Redirect to safer, positive alternative
4. **Remind Model is Not Human**: State clearly you're an AI when relevant
5. **Encourage Introspection**: Prompt child to self-reflect instead of direct answer

#### Match their Age (1 option)
1. **Tailor to Age Group**: Simplify language to be age-appropriate (uses child_age if provided)

#### Defer to Support (2 options)
1. **Defer to Parents**: Defer topic to parent/trusted adult
2. **Defer to Resources**: Suggest appropriate real-world resource

#### Attention Check (1 option)
1. **I read the instructions**: Confirm careful reading of embedded instructions

#### Custom (user-defined)
- User can create custom instruction text
- Stored with unique ID prefixed with `custom_`

### Selection Process

1. User selects up to 3 strategies total (standard + custom combined)
2. User can add custom instructions via text input field
3. Strategies stored in `selectedModerations` Set
4. Custom instructions stored in `customInstructions` array
5. When applying, custom instruction IDs are converted to texts

## 5. Response Generation Flow

### When User Applies Moderation

1. **`applySelectedModerations()` called** (line ~2290)
   - Validates selections
   - Sets `moderationLoading = true`

2. **Separates standard strategies from custom IDs**
   - Standard strategies: Direct strategy names
   - Custom texts: Extracted from `customInstructions` array using IDs

3. **Calls `applyModeration()` API function** with:
   - `moderationTypes`: Array of standard strategy names
   - `customInstructions`: Array of custom instruction texts
   - `originalResponse1`: Original response (for refactoring mode)
   - `highlightedTexts1`: User-highlighted phrases
   - `childAge`: Child's age (for age-appropriate tailoring)
   - `model`: `'gpt-5.2'` (default)

4. **Backend `multi_moderations_openai()`**:
   - Validates and deduplicates moderation types
   - Builds combined instruction list (numbered)
   - Customizes "Tailor to Age Group" if child_age provided
   - Uses **REFACTORING MODE** (since `original_response` provided)
   - Constructs system prompt:
     ```
     You are a child-friendly AI assisting with parent-guided moderation.
     You will be given a child's original prompt and the assistant's original response.
     Your job is to rewrite the response to follow ALL of the following parent-selected rules:
     [combined instructions]
     
     Output STRICTLY as JSON (no extra text):
     { "refactored_response": string, "system_prompt_rule": string }
     Constraints: warm, child-friendly, concise; combined length ≤ 600 chars.
     ```
   - Calls OpenAI API with model `gpt-5.2-chat-latest`
   - Parses JSON response
   - Returns `refactored_response` and `system_prompt_rule`

5. **Frontend creates new `ModerationVersion` object**:
   ```typescript
   {
     response: result.refactored_response,
     strategies: [...standardStrategies],
     customInstructions: usedCustomInstructions, // Array of {id, text}
     highlightedTexts: [...highlightedTexts1],
     moderationResult: result
   }
   ```

6. **Version added to `versions[]` array**
   - `versions = [...versions, newVersion]` (triggers reactivity)

7. **`currentVersionIndex` set to new version**
   - `currentVersionIndex = versions.length - 1`

8. **`showOriginal1` set to `false`**
   - Ensures user sees the new moderated version

9. **Version saved to backend** via `saveModerationSession()`
   - Saves with `version_number: currentVersionIndex + 1`
   - Includes all strategies, custom instructions, highlighted texts
   - `is_final_version: false` until finalized

10. **Selections cleared** for next iteration
    - `selectedModerations = new Set()`
    - `customInstructions = []`
    - `attentionCheckSelected = false`

## 6. Display Logic

### Response Display (`response1HTML` reactive statement, line ~1290)

The displayed response is determined by:

1. **Step 1 (Highlighting)**: Always shows original with highlights
   ```typescript
   if (showInitialDecisionPane && initialDecisionStep === 1) {
     return getHighlightedHTML(originalResponse1, highlightedTexts1);
   }
   ```

2. **If `showOriginal1 === true`**: Shows original with highlighted concerns
   ```typescript
   if (showOriginal1) {
     return getHighlightedHTML(originalResponse1, highlightedTexts1);
   }
   ```

3. **If `showOriginal1 === false`**: Shows current moderated version
   ```typescript
   if (currentVersionIndex >= 0 && currentVersionIndex < versions.length) {
     return versions[currentVersionIndex].response;
   }
   ```

4. **Fallback**: Shows original with highlights
   ```typescript
   return getHighlightedHTML(originalResponse1, highlightedTexts1);
   ```

### Version Navigation UI (lines ~3475-3523)

#### Toggle Button
- **Text**: "View Original" when showing moderated, "View Moderated Version(s)" when showing original
- **Action**: Toggles `showOriginal1`
- **Behavior**: When switching back to moderated, ensures valid version index

#### Navigation Arrows
- **Previous Button**: 
  - Disabled when: `currentVersionIndex <= 0`, version confirmed, or showing original
  - Decrements `currentVersionIndex`
  
- **Next Button**:
  - Disabled when: `currentVersionIndex >= versions.length - 1`, version confirmed, or showing original
  - Increments `currentVersionIndex`

#### Version Counter
- **Format**: `{currentVersionIndex + 1}/{versions.length}`
- **Checkmark**: Shows `✓` prefix if current version is confirmed
- **Display**: `{confirmedVersionIndex !== null && currentVersionIndex === confirmedVersionIndex ? '✓ ' : ''}{currentVersionIndex + 1}/{versions.length}`

### Highlighted Text Display
- When `showOriginal1 === true` and `highlightedTexts1.length > 0`:
  - Shows "Highlighted Concerns" section below response
  - Displays each highlight as removable badge
  - Shows "Change/Add Highlighted Text" button if moderation panel visible

### Applied Strategies Display
- When viewing moderated version (`!showOriginal1`):
  - Shows "Applied Strategies" section below response
  - Displays standard strategies as blue badges
  - Displays custom instructions as purple badges with "Custom: " prefix

## 7. User Decision Points

### Initial Decision (3-Step Flow)

#### Step 1 - Highlight
- **Purpose**: User highlights concerning text (optional)
- **UI**: Text selection enabled on response bubble
- **Actions**:
  - Drag over text to highlight
  - Highlights shown as yellow badges
  - Can remove highlights by clicking badge
  - "Continue" button (green if highlights exist, gray if none)
  - "Skip Scenario" button (marks as not applicable)

#### Step 2 - Reflect
- **Purpose**: User enters reflection
- **UI**: Two input fields:
  - "I feel...": Text input
  - "because...": Textarea
- **Validation**: Both fields required to continue
- **Actions**:
  - "Back" button (returns to Step 1)
  - "Continue" button (disabled until both fields filled)

#### Step 3 - Decide
- **Purpose**: User makes initial decision
- **UI**: Shows reflection summary, two large buttons
- **Actions**:
  - **"Accept" button**: 
    - Calls `saveStep3Decision('accept_original')`
    - Sets `acceptedOriginal = true`
    - Saves with `initial_decision: 'accept_original'`
    - **Still navigates to moderation panel** (allows optional version creation)
  - **"Moderate" button**:
    - Calls `saveStep3Decision('moderate')`
    - Sets `acceptedOriginal = false`
    - Saves with `initial_decision: 'moderate'`
    - Opens moderation panel for strategy selection
  - **"Back" button**: Returns to Step 2

**Important**: Both "Accept" and "Moderate" navigate to the moderation panel. Users who accept can still optionally create moderated versions if they change their mind.

### After Moderation Applied

#### Decision Buttons (shown when `confirmedVersionIndex === null`)

1. **"Moderate Again" button**:
   - Opens moderation panel
   - Expands panel
   - Scrolls to panel
   - Allows creating another version with different strategies

2. **"This is Good" button**:
   - Calls `confirmCurrentVersion()`
   - Sets `confirmedVersionIndex = currentVersionIndex`
   - Hides moderation panel
   - Saves confirmation to state

### Version Switching

- **Toggle Original/Moderated**:
  - "View Original" button toggles `showOriginal1`
  - When switching to moderated, ensures valid version index
  - When viewing original, version navigation disabled

- **Navigate Between Versions**:
  - Previous/Next arrows navigate between versions
  - Disabled when version confirmed or viewing original
  - Version counter shows current position

## 8. Data Persistence

### Immediate Saves

#### Version Creation
- Each version creation saves to backend via `saveModerationSession()`
- **Payload includes**:
  - `version_number`: `currentVersionIndex + 1`
  - `strategies`: Array of standard strategy names
  - `custom_instructions`: Array of custom instruction texts
  - `highlighted_texts`: Array of highlighted phrases
  - `refactored_response`: The moderated response text
  - `is_final_version`: `false` (until finalized)
  - `session_metadata`: Includes reflection, decision timestamp, version index

#### State Persistence
- State saved to localStorage on every change (reactive statement at line ~2323)
- **Saves to**: `moderationScenarioStates_{childId}`
- **Includes**: All state variables in `ScenarioState` interface

#### Session Activity Tracking
- Tracks active time spent on moderation session
- Syncs every 30 seconds via `postSessionActivity()`
- Uses idle threshold of 60 seconds
- Stored in `moderationActiveMs_{childId}_{session}`

### Finalization

#### When All Scenarios Completed
- `finalizeModeration()` called via `POST /workflow/moderation/finalize`
- **Backend Process** (`backend/open_webui/routers/workflow.py`):
  1. Groups sessions by (child_id, scenario_index, attempt_number, session_number)
  2. For each scenario, finds latest created row
  3. Marks latest as `is_final_version: true`
  4. Clears `is_final_version` on all other versions for that scenario

## 9. Key UI Elements

### Response Bubble

- **Location**: Main chat area, left-aligned
- **Content**: 
  - Shows original or moderated response based on `showOriginal1` and `currentVersionIndex`
  - Highlights user-selected text when viewing original
  - Displays applied strategies below response when viewing moderated version
- **Styling**: 
  - Gray background (`bg-gray-100 dark:bg-gray-800`)
  - Rounded corners (`rounded-2xl rounded-tl-sm`)
  - Max width 80%

### Moderation Panel

- **Location**: Below response area
- **Visibility**: Controlled by `moderationPanelVisible`
- **Features**:
  - Collapsible panel with grouped strategy options
  - Custom instruction input field
  - "Apply Moderation" button triggers generation
  - Loading state during API call (`moderationLoading`)
  - Expandable groups for better organization

### Decision Buttons

- **Location**: Below response, after applied strategies
- **Visibility**: Only shown when `confirmedVersionIndex === null`
- **Buttons**:
  - **"Moderate Again"**: Blue button, opens panel for new version
  - **"This is Good"**: Green button, confirms current version

### Initial Decision Pane

- **Location**: Below response area
- **Visibility**: Shown when `showInitialDecisionPane && !hasInitialDecision`
- **Features**:
  - 3-step indicator with progress
  - Step 1: Highlighting interface
  - Step 2: Reflection form
  - Step 3: Accept/Moderate decision

## 10. Special Cases

### Attention Check

#### Detection
- One random scenario has attention check marker `<!--ATTN-CHECK-->`
- Marker appended to response with instructions
- `isAttentionCheckScenario` reactive variable detects marker

#### Behavior
- When user selects "I read the instructions" from Attention Check dropdown:
  1. Immediately saves attention check as passed to backend
  2. Sets `hasInitialDecision = true`
  3. Sets `acceptedOriginal = true`
  4. Sets `step3Completed = true`
  5. Closes panels: `moderationPanelVisible = false`, `showInitialDecisionPane = false`
  6. Saves state to localStorage
  7. Automatically navigates to next scenario after 1 second delay
  8. Shows success message: "✓ Passed attention check! Moving to next scenario..."

#### Tracking
- `attention_check_selected`: Whether option was selected
- `attention_check_passed`: Whether check was passed (saved to database)
- State persists when navigating back

### Custom Scenario

#### Generation
- User can create custom prompt via input field
- `generateCustomScenarioResponse()` function (line ~758):
  1. User enters custom prompt
  2. Calls moderation API with empty strategies to generate baseline response
  3. Response becomes the "original_response" for moderation
  4. Custom prompt stored in `scenarioState.customPrompt`
  5. Treated like any other scenario after generation

#### State Management
- `customScenarioPrompt`: User-entered prompt text
- `customScenarioResponse`: Generated baseline response
- `customScenarioGenerated`: Whether scenario has been generated
- Special handling in `loadScenario()` to restore custom prompt

### Not Applicable

#### Marking
- User can mark scenario as not applicable via "Skip Scenario" button
- `markNotApplicable()` function (line ~1706):
  1. Sets `hasInitialDecision = true`
  2. Sets `markedNotApplicable = true`
  3. Saves session with `initial_decision: 'not_applicable'`
  4. No moderation strategies applied

#### Display
- Shows "Marked as not applicable" indicator below response
- "Undo" button allows unmarking

## Default Model Configuration

The default model is set to **`"gpt-5.2-chat-latest"`** in the following locations:

1. **`backend/open_webui/routers/moderation.py`** (line 18):
   - `ModerationRequest` class: `model: Optional[str] = "gpt-5.2-chat-latest"`

2. **`backend/open_webui/routers/moderation.py`** (line 29):
   - `FollowUpPromptRequest` class: `model: Optional[str] = "gpt-5.2-chat-latest"`

3. **`backend/open_webui/utils/moderation.py`** (line 37):
   - `multi_moderations_openai()` function: `model: str = "gpt-5.2-chat-latest"`

4. **`backend/open_webui/utils/moderation.py`** (line 188):
   - `generate_second_pass_prompt()` function: `model: str = "gpt-5.2-chat-latest"`

5. **`src/lib/apis/moderation/index.ts`** (line 168):
   - `applyModeration()` function: `model: 'gpt-5.2-chat-latest'` (in request body)

## Files Reference

1. **Frontend Main Component**: `src/routes/(app)/moderation-scenario/+page.svelte`
2. **API Client**: `src/lib/apis/moderation/index.ts`
3. **Backend Router**: `backend/open_webui/routers/moderation.py`
4. **Backend Utils**: `backend/open_webui/utils/moderation.py`
5. **Workflow Router**: `backend/open_webui/routers/workflow.py` (finalization)
6. **Database Models**: `backend/open_webui/models/moderation.py`
7. **Existing Documentation**: `docs/MODERATION_SURVEY_FLOW.md`

## Stale Code (Commented Out)

The following code has been commented out as it is no longer used:

1. **`startModerating()` function**: DEPRECATED - replaced by unified 3-step flow
2. **`finishHighlighting()` function**: No longer used - highlighting now in Step 1
3. **`submitReflection()` function**: No longer used - reflection now in Step 2
4. **`satisfiedWithOriginalFromPanel()` function**: Not found to be called from UI
5. **`showReflectionModal` variable**: Replaced by Step 2 in unified flow
6. **`highlightingMode` variable**: No longer used - highlighting now in Step 1

All stale code is marked with `// STALE:` comments for easy identification and future removal.

## Summary

The moderation tool provides a comprehensive workflow for parents to review and modify AI responses to child prompts. The system supports:

- **Flexible Strategy Selection**: Up to 3 strategies (standard + custom)
- **Multiple Versions**: Create and compare different moderated versions
- **State Persistence**: All decisions and versions saved immediately
- **User-Friendly Interface**: Clear 3-step initial decision flow
- **Special Handling**: Attention checks, custom scenarios, and not applicable options
- **Flexible Decision Flow**: Both "Accept" and "Moderate" decisions allow access to moderation panel

The architecture separates concerns between frontend state management, API communication, and backend processing, ensuring a robust and maintainable system.

