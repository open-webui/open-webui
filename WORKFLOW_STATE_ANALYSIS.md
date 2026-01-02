# Workflow State Analysis

## Summary
The moderation survey workflow requires tracking multiple state variables to manage the complete user journey. The workflow has been simplified by removing the "accept original" option and converting satisfaction to a 1-5 Likert scale.

## Terminal States

The workflow has these terminal states (necessary for display/continue logic):
- **skipped**: `markedNotApplicable === true`
- **highlighted**: `step1Completed === true && highlightedTexts1.length > 0`
- **assessed**: `step2Completed === true && concernLevel !== null`
- **try again**: `satisfactionLevel !== null && nextAction === 'try_again'`
- **move on (complete)**: `nextAction === 'move_on' || confirmedVersionIndex !== null`

If next state is not present, display previous state for continue.

## Complete State Variables Required

### 1. Step Completion Flags (Navigation State)
- `step1Completed: boolean` - Has user completed Step 1 (Highlight)?
- `step2Completed: boolean` - Has user completed Step 2 (Assess)?
- `step3Completed: boolean` - Has user completed Step 3 (Update)?

**Purpose**: These determine which step UI to show (derived via `initialDecisionStep` reactive statement)

### 2. Decision/Completion State
- `markedNotApplicable: boolean` - Did user skip this scenario?

**Purpose**: Track the final decision state and whether scenario is completed

**Note**: 
- `acceptedOriginal` has been removed - users can no longer accept original response without moderation.
- `hasInitialDecision` has been removed - completion is now determined by `markedNotApplicable || confirmedVersionIndex !== null`
- `initialDecisionChoice` has been removed - it was never used in logic, only stored

### 3. Step 1 (Highlight) Data
- `highlightedTexts1: string[]` - Array of text selections from Step 1

**Purpose**: Store the user's highlighted concerns

### 4. Step 2 (Assess) Data
- `concernLevel: number | null` - Concern level (1-5 Likert scale)
- `concernReason: string` - Explanation for concern level

**Purpose**: Store the concern assessment data

### 5. Step 3 (Update) Data
- `satisfactionLevel: number | null` - Satisfaction level (1-5 Likert scale)
  - 1 = Very Dissatisfied
  - 2 = Dissatisfied
  - 3 = Neutral
  - 4 = Satisfied
  - 5 = Very Satisfied
- `satisfactionReason: string` - Why satisfied/unsatisfied (required if level 1-3)
- `nextAction: 'try_again' | 'move_on' | null` - What to do next
  - Determined by satisfaction level: 1-3 = try_again, 4-5 = move_on

**Purpose**: Store satisfaction check data after version creation

**Note**: Changed from binary `satisfactionStatus: 'satisfied' | 'unsatisfied'` to 1-5 Likert scale.

### 6. Version Management State
- `versions: ModerationVersion[]` - Array of all moderated versions created
- `currentVersionIndex: number` - Which version is currently being viewed
- `confirmedVersionIndex: number | null` - Which version was confirmed as final

**Purpose**: Track all moderated versions and which one is selected/confirmed

### 7. Moderation Strategy State
- `selectedModerations: Set<string>` - Which moderation strategies are selected
- `customInstructions: Array<{id: string, text: string}>` - Custom instructions added
- `attentionCheckSelected: boolean` - Was attention check selected?

**Purpose**: Track what strategies user wants to apply

### 8. UI Visibility State

**Derived (via reactive statements):**
- `showInitialDecisionPane: boolean` - Derived from: `!step3Completed && !markedNotApplicable && (initialDecisionStep >= 1 && initialDecisionStep <= 3)`
- `moderationPanelVisible: boolean` - Derived from: `initialDecisionStep === 3 && confirmedVersionIndex === null && !markedNotApplicable && step2Completed && versions.length === 0`
- `showOriginal1: boolean` - Derived from: `!showComparisonView || (initialDecisionStep === 1)`

**Stored (user preferences):**
- `showComparisonView: boolean` - User preference when versions exist - can toggle between original and comparison
- `moderationPanelExpanded: boolean` - User preference for panel expansion state

**Purpose**: Control which UI elements are visible

### 9. Loading/Processing State
- `moderationLoading: boolean` - Is moderation request in progress?
- `customScenarioGenerating: boolean` - Is custom scenario being generated?

**Purpose**: Track async operations

## State Dependencies

The workflow state has simplified interdependencies:

1. **Step Navigation**: `initialDecisionStep` is derived from completion flags:
   ```typescript
   $: initialDecisionStep = (() => {
     if (!step1Completed) return 1;
     if (!step2Completed) return 2;
     if (!step3Completed) return 3;
     return 3; // Stay on step 3 even when completed
   })();
   ```

2. **Scenario Completion**: `currentScenarioCompleted` depends on:
   - `markedNotApplicable` OR `confirmedVersionIndex !== null`
   - (Removed: `acceptedOriginal`, `hasInitialDecision`, `initialDecisionChoice`)

3. **Panel Visibility**: Derived from:
   - Completion flags
   - Decision state
   - Version state
   - (No longer manually set)

4. **Step 3 Satisfaction Check**: Only shown when:
   - `versions.length > 0`
   - `showComparisonView === true`
   - `satisfactionLevel === null`

5. **Satisfaction Action Logic**:
   - `satisfactionLevel <= 3` → `nextAction = 'try_again'` (requires reason)
   - `satisfactionLevel >= 4` → `nextAction = 'move_on'` (reason optional)

## Changes from Previous Version

1. **Removed `acceptedOriginal`**: Users can no longer accept original response without moderation
2. **Satisfaction Scale**: Changed from binary yes/no to 1-5 Likert scale
3. **UI Visibility Simplification**: Three UI visibility variables are now derived via reactive statements instead of manually set
4. **Terminal States**: Added explicit terminal state model for display/continue logic

## Conclusion

**We need to track 20+ state variables** to properly manage the workflow. The completion flags tell us where we are in the flow, but we need all the other variables to:
- Store user input from each step
- Track decisions made
- Manage version creation and selection
- Control UI visibility (mostly derived)
- Handle async operations

The state model has been simplified by:
- Removing redundant `acceptedOriginal` state
- Converting satisfaction to Likert scale for better granularity
- Deriving UI visibility from other state variables
- Using terminal states for clearer flow control
