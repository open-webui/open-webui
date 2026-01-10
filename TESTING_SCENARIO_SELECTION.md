# Testing Scenario Selection Feature Locally

This guide walks you through testing the new scenario assignment and tracking system locally.

## Prerequisites

1. **Backend environment**: Python 3.11 with conda environment `open-webui`
2. **Frontend environment**: Node.js (for npm)
3. **Database**: SQLite (default) or PostgreSQL - migrations should be run
4. **Scenarios loaded**: The 50 scenarios from JSON should be in the database

## Step 1: Verify Database Setup

### Check if scenarios are loaded:

```bash
cd backend
conda activate open-webui
python -c "from open_webui.models.scenarios import Scenarios; scenarios = Scenarios.get_all(is_active=True, is_validated=True); print(f'Found {len(scenarios)} active scenarios')"
```

Expected output: `Found 50 active scenarios`

### If scenarios are not loaded, load them:

```bash
cd backend
conda activate open-webui
python -m open_webui.scripts.load_scenarios_from_json --json-file ../Persona_generation/random_50_subset.json
```

## Step 2: Start the Backend Server

### Terminal 1 - Backend:

```bash
cd backend
conda activate open-webui
export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:8080"
uvicorn open_webui.main:app --port 8080 --host localhost --forwarded-allow-ips '*' --reload
```

Or use the dev script:

```bash
cd backend
conda activate open-webui
./dev.sh
```

**Verify backend is running:**
- Check `http://localhost:8080/health` - should return `{"status": "ok"}`
- Check backend logs for any errors

## Step 3: Start the Frontend Development Server

### Terminal 2 - Frontend:

```bash
# In project root (not backend directory)
npm install  # Only needed first time or after dependency changes
npm run dev
```

**Expected output:**
- Frontend should start on `http://localhost:5173` (or similar port)
- Vite dev server will proxy `/api` requests to `http://localhost:8080`

## Step 4: Test API Endpoints Directly

### 4.1 Get Authentication Token

First, you'll need to authenticate. You can either:
- Use the web UI to log in and copy the token from browser localStorage
- Or create a test user via the signup endpoint

```bash
# Get token from browser (after logging in via UI)
# In browser console: localStorage.getItem('token')
export TOKEN="your-auth-token-here"
export USER_ID="your-user-id-here"
```

### 4.2 Test Scenario Assignment Endpoint

```bash
# Assign a scenario
curl -X POST "http://localhost:8080/api/v1/moderation/scenarios/assign" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "participant_id": "'$USER_ID'",
    "child_profile_id": null,
    "assignment_position": 0,
    "alpha": 1.0
  }' | jq
```

**Expected response:**
```json
{
  "assignment_id": "uuid-here",
  "scenario_id": "scenario_xxxx",
  "prompt_text": "...",
  "response_text": "...",
  "assignment_position": 0,
  "sampling_audit": {
    "eligible_pool_size": 50,
    "n_assigned_before": 0,
    "weight": 1.0,
    "sampling_prob": 0.02
  }
}
```

**What to verify:**
- ✅ `assignment_id` is generated
- ✅ `scenario_id` matches a scenario from the database
- ✅ `sampling_audit` shows correct pool size (50 scenarios)
- ✅ `n_assigned_before` is 0 for first assignment
- ✅ `sampling_prob` is approximately 1/50 = 0.02

### 4.3 Test Multiple Assignments (Verify Weighted Sampling)

```bash
# Assign 10 scenarios to see weighted sampling in action
for i in {0..9}; do
  echo "Assignment $i:"
  curl -s -X POST "http://localhost:8080/api/v1/moderation/scenarios/assign" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{
      \"participant_id\": \"$USER_ID\",
      \"assignment_position\": $i,
      \"alpha\": 1.0
    }" | jq -r '.scenario_id + " (n_assigned_before: " + (.sampling_audit.n_assigned_before | tostring) + ")"'
  sleep 0.5
done
```

**What to verify:**
- ✅ Different scenarios are selected (unless pool is exhausted)
- ✅ Scenarios with lower `n_assigned_before` are more likely to be selected
- ✅ As scenarios get assigned more, their `sampling_prob` decreases

### 4.4 Test Start Endpoint

```bash
# Get an assignment_id from previous step
export ASSIGNMENT_ID="assignment-uuid-from-step-4.2"

curl -X POST "http://localhost:8080/api/v1/moderation/scenarios/start" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "assignment_id": "'$ASSIGNMENT_ID'"
  }' | jq
```

**Expected response:**
```json
{
  "status": "started",
  "assignment_id": "uuid-here"
}
```

### 4.5 Test Complete Endpoint

```bash
# First, create a highlight to test issue_any calculation
# (Highlights are needed for issue_any calculation)

# Then complete the assignment
curl -X POST "http://localhost:8080/api/v1/moderation/scenarios/complete" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "assignment_id": "'$ASSIGNMENT_ID'"
  }' | jq
```

**Expected response:**
```json
{
  "status": "completed",
  "assignment_id": "uuid-here",
  "issue_any": 0  # or 1 if highlights exist
}
```

**What to verify:**
- ✅ Status changes to "completed"
- ✅ `issue_any` is 0 if no highlights, 1 if highlights exist
- ✅ Counter `n_completed` increments in database

### 4.6 Test Skip Endpoint

```bash
# Get a new assignment for skipping
export SKIP_ASSIGNMENT_ID="new-assignment-uuid"

curl -X POST "http://localhost:8080/api/v1/moderation/scenarios/skip" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "assignment_id": "'$SKIP_ASSIGNMENT_ID'",
    "skip_stage": "step1",
    "skip_reason": "not_applicable",
    "skip_reason_text": "Test skip"
  }' | jq
```

**What to verify:**
- ✅ Status changes to "skipped"
- ✅ Skip details are saved
- ✅ Counter `n_skipped` increments
- ✅ Scenario is excluded from future assignments for this participant

### 4.7 Test Abandon Endpoint

```bash
# Get a new assignment for abandoning
export ABANDON_ASSIGNMENT_ID="new-assignment-uuid"

curl -X POST "http://localhost:8080/api/v1/moderation/scenarios/abandon" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "assignment_id": "'$ABANDON_ASSIGNMENT_ID'"
  }' | jq
```

**Expected response:**
```json
{
  "status": "abandoned",
  "assignment_id": "uuid-here",
  "reassigned": true,
  "new_assignment_id": "new-uuid",
  "new_scenario_id": "scenario_xxxx",
  "new_prompt_text": "...",
  "new_response_text": "...",
  "new_sampling_audit": {...}
}
```

**What to verify:**
- ✅ Original assignment is marked "abandoned"
- ✅ `n_abandoned` counter increments
- ✅ New assignment is automatically created (reassigned)
- ✅ Abandoned scenario can still be assigned again (not excluded)

### 4.8 Test Highlights API

```bash
# Create a highlight
curl -X POST "http://localhost:8080/api/v1/moderation/highlights" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "assignment_id": "'$ASSIGNMENT_ID'",
    "selected_text": "example text",
    "source": "response",
    "start_offset": 10,
    "end_offset": 22
  }' | jq

# Get highlights for an assignment
curl -X GET "http://localhost:8080/api/v1/moderation/highlights/$ASSIGNMENT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq
```

## Step 5: Test Frontend Integration

### 5.1 Access the Moderation Scenario Page

1. Open browser to `http://localhost:5173`
2. Log in with your credentials
3. Navigate to the Review Scenarios page

### 5.2 Verify Scenario Loading

**What to check in browser console:**
- ✅ Should see: `✅ Loaded X scenarios from backend` (where X ≤ 50)
- ✅ Should NOT see: `✅ Loaded 500 scenarios from scenario bank` (old CSV system)
- ✅ Each scenario should have `assignment_id` and `scenario_id`

**What to check in Network tab:**
- ✅ POST requests to `/api/v1/moderation/scenarios/assign` (6 times for SCENARIOS_PER_SESSION=6)
- ✅ Each request returns a different scenario
- ✅ Responses include `sampling_audit` with correct values

### 5.3 Test Scenario Lifecycle

1. **Start a scenario:**
   - Click on a scenario to load it
   - Check Network tab for POST `/api/v1/moderation/scenarios/start`
   - Verify `assignmentStarted` is set in scenario state

2. **Create highlights:**
   - Drag to select text in the response
   - Check Network tab for POST `/api/v1/moderation/highlights`
   - Verify highlight is saved with `assignment_id`, `start_offset`, `end_offset`

3. **Complete a scenario:**
   - Complete Step 1 (highlight concerns)
   - Complete Step 2 (submit concern reason)
   - Check Network tab for POST `/api/v1/moderation/scenarios/complete`
   - Verify `issue_any` is calculated correctly (0 if no highlights, 1 if highlights exist)

4. **Skip a scenario:**
   - Click "Skip" on a scenario
   - Check Network tab for POST `/api/v1/moderation/scenarios/skip`
   - Verify scenario is excluded from future assignments

### 5.4 Test Weighted Sampling Behavior

**Method 1: Console inspection**
- Open browser console
- After loading scenarios, check: `scenarioStates.get(0)`
- Each scenario should have different `scenario_id`
- Repeatedly refresh and load scenarios - should see different scenarios selected

**Method 2: Database inspection**
- Query the database to see `n_assigned` counters:
```bash
cd backend
conda activate open-webui
python -c "from open_webui.models.scenarios import Scenarios; scenarios = Scenarios.get_all(); print('\n'.join([f'{s.scenario_id}: n_assigned={s.n_assigned}' for s in scenarios[:10]]))"
```

- After multiple assignments, scenarios with lower `n_assigned` should be selected more often

### 5.5 Test Abandonment Detection

**Manual test:**
1. Start a scenario
2. Wait 30+ minutes (or temporarily reduce `ABANDONMENT_TIMEOUT_MS` in code)
3. Check if scenario is automatically abandoned and reassigned

**Quick test (modify timeout temporarily):**
- In `+page.svelte`, change `ABANDONMENT_TIMEOUT_MS` to `60000` (1 minute)
- Start a scenario but don't complete it
- Wait 1+ minute
- Check Network tab for POST `/api/v1/moderation/scenarios/abandon`
- Verify new assignment is created

## Step 6: Verify Database State

### Check scenario counters:

```bash
cd backend
conda activate open-webui
python -c "
from open_webui.models.scenarios import Scenarios
scenarios = Scenarios.get_all()
print('Scenario Assignment Statistics:')
print('=' * 60)
for s in sorted(scenarios, key=lambda x: x.n_assigned, reverse=True)[:10]:
    print(f'{s.scenario_id[:20]}... | Assigned: {s.n_assigned:3d} | Completed: {s.n_completed:3d} | Skipped: {s.n_skipped:3d} | Abandoned: {s.n_abandoned:3d}')
"
```

**What to verify:**
- ✅ Counters increment correctly
- ✅ Most scenarios should have similar `n_assigned` (due to weighted sampling)
- ✅ `n_completed` + `n_skipped` should match number of completed/skipped assignments

### Check assignments table:

```bash
python -c "
from open_webui.models.scenarios import ScenarioAssignments, AssignmentStatus
assignments = ScenarioAssignments.get_by_participant('your-user-id-here')
print(f'Total assignments: {len(assignments)}')
print('Status breakdown:')
status_counts = {}
for a in assignments:
    status_counts[a.status] = status_counts.get(a.status, 0) + 1
for status, count in status_counts.items():
    print(f'  {status}: {count}')
"
```

## Step 7: Test Edge Cases

### 7.1 Exhausted Pool Test

```bash
# Complete or skip all 50 scenarios
# Then try to assign a new scenario
# Should get: 404 "No eligible scenarios available"
```

### 7.2 Concurrent Assignment Test

```bash
# Run multiple assignment requests simultaneously
for i in {1..5}; do
  curl -X POST "http://localhost:8080/api/v1/moderation/scenarios/assign" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"participant_id\": \"$USER_ID\", \"assignment_position\": $i}" &
done
wait

# Verify all requests succeeded and got different scenarios
```

### 7.3 Abandoned Scenario Reassignment Test

```bash
# 1. Assign a scenario
# 2. Abandon it
# 3. Assign again - abandoned scenario should be eligible again
# 4. Complete/skip it
# 5. Try to assign again - should NOT get the same scenario (it's now completed/skipped)
```

## Common Issues and Troubleshooting

### Issue: "No eligible scenarios available"

**Causes:**
- All scenarios are completed/skipped for this participant
- No scenarios are marked as `is_active=True` or `is_validated=True`
- Scenarios not loaded in database

**Fix:**
```bash
# Check scenario status
python -c "from open_webui.models.scenarios import Scenarios; print(f'Active: {len(Scenarios.get_all(is_active=True))}, Validated: {len(Scenarios.get_all(is_validated=True))}')"

# Reload scenarios if needed
python -m open_webui.scripts.load_scenarios_from_json --json-file ../Persona_generation/random_50_subset.json
```

### Issue: Frontend still loading from CSV (500 scenarios)

**Causes:**
- Frontend code not updated
- Browser cache

**Fix:**
- Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
- Check browser console for API calls to `/moderation/scenarios/assign`

### Issue: Assignment ID not found

**Causes:**
- Frontend trying to use assignment_id before scenario is assigned
- State not properly saved

**Fix:**
- Check that `loadRandomScenarios()` completes before loading first scenario
- Verify assignment_ids are stored in `scenarioStates`

### Issue: Floating point precision errors in sampling

**Status:** ✅ Fixed in latest code
- The new algorithm checks ranges before adding to cumulative
- Added safety fallback for edge cases

## Success Criteria

✅ **Backend:**
- Weighted sampling formula works correctly
- Eligible scenarios exclude completed/skipped, allow abandoned
- Counters increment atomically
- Assignment lifecycle (assign → start → complete/skip/abandon) works

✅ **Frontend:**
- Loads scenarios from backend API (not CSV)
- Tracks assignment_ids correctly
- Calls lifecycle endpoints at appropriate times
- Saves highlights with proper offsets

✅ **Integration:**
- Complete flow works end-to-end
- Weighted sampling distributes scenarios evenly over time
- Abandonment triggers reassignment
- Skipped scenarios are excluded from future assignments

## Next Steps After Testing

If all tests pass:
1. Commit the fixes
2. Test with multiple users/participants
3. Monitor database to ensure counters update correctly
4. Verify weighted sampling distributes scenarios evenly

