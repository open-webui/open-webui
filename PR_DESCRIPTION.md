# Fix Scenario Generation and Attention Check Flow

## Summary

This PR fixes critical issues with scenario generation (character encoding mismatch) and improves the attention check flow with automatic navigation and proper state persistence. It also includes code quality improvements and documentation updates.

## Key Changes

### 🔧 Bug Fixes

1. **Fixed Character Encoding Mismatch in Scenario Generation**
   - **Issue**: Characteristic "Is suspicious of others' intentions" failed to generate scenarios due to curly apostrophe (U+2019) vs straight apostrophe (U+0027) mismatch
   - **Solution**: Added `normalizeQuotes()` function to handle encoding differences
   - **Files**: `src/lib/data/personalityQuestions.ts`
   - **Impact**: All characteristics now correctly match JSON keys regardless of quote encoding

2. **Fixed Attention Check Flow**
   - **Issue**: Selecting "I read the instructions" didn't navigate to next scenario and state didn't persist
   - **Solution**: 
     - Auto-navigates to next scenario when attention check is selected
     - Properly sets all completion flags (`hasInitialDecision`, `acceptedOriginal`, `step3Completed`)
     - Saves state to localStorage and backend for persistence
     - Shows "Passed attention check" message
   - **Files**: `src/routes/(app)/moderation-scenario/+page.svelte`
   - **Impact**: Attention check now works as intended with proper state management

3. **Fixed `afterNavigate` Initialization Error**
   - **Issue**: "Function called outside component initialization" error
   - **Solution**: Moved `afterNavigate` callback to top level with proper type safety
   - **Files**: `src/routes/(app)/moderation-scenario/+page.svelte`
   - **Impact**: Eliminates runtime errors on navigation

4. **Fixed OpenAI API Key Detection**
   - **Issue**: Backend couldn't find OpenAI API keys from environment variables
   - **Solution**: Added fallback to read `OPENAI_API_KEY` directly from environment if not in config
   - **Files**: `backend/open_webui/routers/moderation.py`, `backend/dev.sh`
   - **Impact**: API keys now work correctly from environment variables

### ✨ Improvements

1. **Added Fallback for Zero Scenario Generation**
   - Automatically adds default characteristics and retries if no scenarios are generated
   - Shows user-facing error message if retry fails
   - **Files**: `src/routes/(app)/moderation-scenario/+page.svelte`

2. **Code Quality Improvements**
   - Extracted duplicate default characteristics to constant (`DEFAULT_CHARACTERISTICS`)
   - Improved type safety (removed `as any`, added proper type checks)
   - Enhanced error handling with user-facing messages
   - **Files**: `src/routes/(app)/moderation-scenario/+page.svelte`

3. **Updated Attention Check Instructions**
   - Clarified that "I read the instructions" is in the "Attention Check" dropdown
   - Updated instructions to match new 3-step initial decision flow
   - **Files**: `src/routes/(app)/moderation-scenario/+page.svelte`

4. **Documentation Updates**
   - Updated `docs/MODERATION_SURVEY_FLOW.md` to reflect new attention check behavior
   - Documented character encoding fix
   - **Files**: `docs/MODERATION_SURVEY_FLOW.md`

## Files Changed

### Frontend
- `src/routes/(app)/moderation-scenario/+page.svelte` - Main moderation scenario component
- `src/lib/data/personalityQuestions.ts` - Scenario generation with encoding fix

### Backend
- `backend/open_webui/routers/moderation.py` - OpenAI API key fallback
- `backend/dev.sh` - Environment variable exports

### Documentation
- `docs/MODERATION_SURVEY_FLOW.md` - Updated attention check flow documentation

## Testing Recommendations

1. **Scenario Generation**:
   - Test with child profile containing "Is suspicious of others' intentions" characteristic
   - Verify scenarios are generated correctly
   - Test fallback when 0 scenarios are initially generated

2. **Attention Check Flow**:
   - Select "I read the instructions" on an attention check scenario
   - Verify it navigates to next scenario automatically
   - Navigate back and verify state persists (panels don't reopen)

3. **API Key**:
   - Verify OpenAI API works with environment variables set

## Breaking Changes

None - all changes are backward compatible.

## Related Issues

- Fixes scenario generation failures for characteristics with special characters
- Fixes attention check navigation and state persistence
- Resolves initialization errors on navigation

