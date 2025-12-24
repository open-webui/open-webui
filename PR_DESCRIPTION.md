# Refine Moderation Workflow: UI Improvements and Step 4 Integration

## Overview
This PR refines the moderation scenario workflow by improving UI consistency, fixing navigation issues, and enhancing the user experience throughout the 4-step decision flow (Highlight, Reflect, Decide, Update).

## Key Changes

### UI/UX Improvements
- **Assignment Steps Sidebar**: Close by default on moderation scenarios page (scenarios sidebar unchanged)
- **Confirm Acceptance Button**: Moved above strategy instructions to reduce nudging
- **Back Button Placement**: Standardized to top-right alignment across all steps
- **Highlighting Feature**: Disabled when original response is accepted to prevent confusion

### Step 4 (Update) Workflow Enhancements
- **Review Buttons Preservation**: Maintain review buttons ("Moderate Again" / "This is Good") when navigating back from Step 3
- **Dual Layout Maintenance**: Keep side-by-side comparison view visible when clicking "Moderate Again"
- **Moderation Panel Visibility**: Automatically hide after creating new version to show review buttons
- **Single View on Accept**: Switch to single view with "Original response accepted as satisfactory" message when accepting original
- **Back Button**: Added to "Another version is confirmed" message for navigation

### Custom Scenario Flow
- **4-Step Process Initialization**: Properly initialize unified initial decision flow after custom scenario generation
- Ensures custom scenarios follow the same workflow as regular scenarios

### Configuration Changes
- **Scenario Limit**: Reduced from 10 to 5 scenarios with clear documentation for future updates
- **Model Update**: Updated default moderation model to `gpt-5.2-chat-latest`

### Sidebar Responsiveness
- **Toggle Button Behavior**: Sidebar now respects button state on all screen sizes (not gated by width logic)
- **Visibility Fixes**: Restored hide/show buttons and "Scenarios" reopen button visibility

### Documentation
- Added comprehensive moderation tool documentation
- Documented stale code analysis
- Added comments for scenario limit configuration

## Technical Details

### Files Modified
- `src/routes/(app)/moderation-scenario/+page.svelte` - Main moderation workflow logic and UI
- `src/lib/data/personalityQuestions.ts` - Scenario limit configuration
- `backend/open_webui/routers/moderation.py` - Model update
- `backend/open_webui/utils/moderation.py` - Model update
- `src/lib/apis/moderation/index.ts` - Model update
- `vite.config.ts` - Dynamic backend port configuration
- Various sidebar and layout components

### Testing
- ✅ Tested merge with `origin/main` - no conflicts detected
- ✅ All workflow steps tested (Highlight, Reflect, Decide, Update)
- ✅ Custom scenario flow verified
- ✅ Navigation between steps verified
- ✅ Review buttons behavior verified

## Breaking Changes
None - all changes are backward compatible and improve existing functionality.

## Related Issues
- Integrates moderation as Step 4 in unified decision flow
- Fixes sidebar visibility and responsiveness issues
- Resolves navigation issues in moderation workflow
