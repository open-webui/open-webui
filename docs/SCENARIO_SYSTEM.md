# Scenario System Documentation

## Overview

The scenario system manages the assignment and tracking of review scenarios for participants. It uses weighted sampling to ensure balanced coverage across scenarios and tracks the complete lifecycle of each assignment.

## Architecture

### Database Schema

#### `scenarios` Table
Canonical record for each scenario with metadata and counters.

**Columns:**
- `scenario_id` (PK): Unique identifier. For uploaded scenarios, uses UUID format (`scenario_{uuid}`). For scenarios loaded via script, uses content hash (`scenario_{hash}`).
- `prompt_text`: The child's question/prompt
- `response_text`: The AI model's response
- `set_name`: Optional set identifier (e.g., 'pilot', 'scaled'). Used for batch management and active set control. Does NOT affect scenario selection logic (which uses `is_active`).
- `trait`: Personality trait (e.g., 'Agreeableness', 'Conscientiousness')
- `polarity`: 'positive', 'negative', or 'neutral'
- `prompt_style`: Prompt style (e.g., 'Journalistic', 'Should I')
- `domain`: Domain category (e.g., 'Internet Interaction', 'Self')
- `source`: Source identifier ('json_file', 'api_generated', 'manual', 'admin_upload')
- `model_name`: Model that produced the response
- `is_active`: Whether scenario is shown to users
- `n_assigned`: Counter for number of times assigned
- `n_completed`: Counter for number of times completed
- `n_skipped`: Counter for number of times skipped
- `n_abandoned`: Counter for number of times abandoned
- `created_at`: Timestamp
- `updated_at`: Timestamp

#### `scenario_assignments` Table
One row per exposure to a scenario, tracking the assignment lifecycle.

**Columns:**
- `assignment_id` (PK): UUID
- `participant_id`: User ID
- `scenario_id` (FK): Reference to scenarios table
- `child_profile_id`: Optional child profile identifier
- `status`: 'assigned', 'started', 'completed', 'skipped', or 'abandoned'
- `assigned_at`: Timestamp when assigned
- `started_at`: Timestamp when started
- `ended_at`: Timestamp when ended
- `alpha`: Weighted sampling alpha parameter used
- `eligible_pool_size`: Number of eligible scenarios at assignment time
- `n_assigned_before`: n_assigned counter value before this assignment
- `weight`: Calculated weight for this scenario
- `sampling_prob`: Realized sampling probability
- `assignment_position`: Position in session (0-indexed)
- `issue_any`: 0, 1, or NULL (calculated from highlights for completed)
- `skip_stage`: Stage where skip occurred
- `skip_reason`: Reason code for skip
- `skip_reason_text`: Optional text explanation

**Constraints:**
- Partial unique constraint: (participant_id, scenario_id, status) WHERE status != 'abandoned'

#### `attention_check_scenarios` Table
Attention check scenarios used for quality control.

**Columns:**
- `scenario_id` (PK): Unique identifier. For uploaded attention checks, uses UUID format (`ac_{uuid}`). When created via upsert, uses content hash (`ac_{hash}`).
- `prompt_text`: Attention check question
- `response_text`: Attention check response
- `trait_theme`: Optional trait theme (e.g., 'attention_check')
- `trait_phrase`: Optional trait phrase
- `sentiment`: Optional sentiment
- `trait_index`: Optional trait index
- `prompt_index`: Optional prompt index
- `set_name`: Optional set identifier
- `is_active`: Whether attention check is active
- `source`: Source identifier
- `created_at`: Timestamp
- `updated_at`: Timestamp

#### `selections` Table (Updated)
Stores highlight spans with assignment tracking.

**New Columns:**
- `assignment_id` (FK): Reference to scenario_assignments
- `start_offset`: Character offset where selection starts
- `end_offset`: Character offset where selection ends

### Data Flow

```
1. Participant requests assignment
   ↓
2. Backend performs weighted sampling
   - Filters eligible scenarios (excludes completed/skipped, allows abandoned)
   - Calculates weights: weight = 1 / (n_assigned + 1)^alpha
   - Samples using cumulative probability
   ↓
3. Create assignment record (status: 'assigned')
   - Store sampling audit fields
   - Increment scenarios.n_assigned counter
   ↓
4. Frontend loads scenario
   ↓
5. Call /start endpoint (status: 'started')
   - Set started_at timestamp
   - Start abandonment timeout (30 minutes)
   ↓
6. User interacts with scenario
   - Creates highlights → stored with assignment_id
   - Completes steps 1 & 2 (identification flow)
   ↓
7. Call /complete endpoint (status: 'completed')
   - Calculate issue_any from highlights (1 if highlights exist, 0 otherwise)
   - Set ended_at timestamp
   - Increment scenarios.n_completed counter
   ↓
OR

7. Call /skip endpoint (status: 'skipped')
   - Record skip stage, reason, reason_text
   - Set ended_at timestamp
   - Increment scenarios.n_skipped counter
   - Scenario excluded from future assignments for this participant
   ↓
OR

7. Abandonment detected (status: 'abandoned')
   - 30 minutes of inactivity triggers /abandon endpoint
   - Set ended_at timestamp
   - Increment scenarios.n_abandoned counter
   - Automatically trigger new assignment (reassignment)
   - Original abandoned scenario remains eligible for future assignments
```

### Weighted Sampling Algorithm

**Formula:** `p(s) ∝ 1/(n_s + 1)^α`

Where:
- `p(s)`: Probability of selecting scenario `s`
- `n_s`: Number of times scenario `s` has been assigned (`n_assigned` counter)
- `α`: Alpha parameter (default: 1.0, higher = more aggressive balancing)

**Implementation:**
1. Get eligible scenarios (exclude completed/skipped for participant, allow abandoned)
2. Calculate weight for each: `weight = 1.0 / (n_assigned + 1)^alpha`
3. Normalize to probabilities: `prob = weight / sum(weights)`
4. Use cumulative distribution for weighted random selection

**Example:**
- Scenario A: n_assigned=0 → weight=1.0
- Scenario B: n_assigned=1 → weight=0.5
- Scenario C: n_assigned=2 → weight=0.33
- Total weight = 1.83
- Probabilities: A=54.6%, B=27.3%, C=18.0%

## API Endpoints

### Participant Endpoints

#### `POST /api/v1/moderation/scenarios/assign`
Assign a scenario using weighted sampling.

**Request:**
```json
{
  "participant_id": "user-id",
  "child_profile_id": "child-id",
  "assignment_position": 0,
  "alpha": 1.0
}
```

**Response:**
```json
{
  "assignment_id": "uuid",
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

#### `POST /api/v1/moderation/scenarios/start`
Mark an assignment as started.

**Request:**
```json
{
  "assignment_id": "uuid"
}
```

#### `POST /api/v1/moderation/scenarios/complete`
Mark an assignment as completed and calculate issue_any.

**Request:**
```json
{
  "assignment_id": "uuid"
}
```

**Response:**
```json
{
  "status": "completed",
  "assignment_id": "uuid",
  "issue_any": 1
}
```

#### `POST /api/v1/moderation/scenarios/skip`
Mark an assignment as skipped.

**Request:**
```json
{
  "assignment_id": "uuid",
  "skip_stage": "step1",
  "skip_reason": "not_applicable",
  "skip_reason_text": "Optional explanation"
}
```

#### `POST /api/v1/moderation/scenarios/abandon`
Mark an assignment as abandoned and trigger reassignment.

**Request:**
```json
{
  "assignment_id": "uuid"
}
```

**Response:**
```json
{
  "status": "abandoned",
  "assignment_id": "uuid",
  "reassigned": true,
  "new_assignment_id": "uuid",
  "new_scenario_id": "scenario_yyyy",
  "new_prompt_text": "...",
  "new_response_text": "..."
}
```

#### `GET /api/v1/moderation/attention-checks/random`
Get a random active attention check scenario.

**Response:**
```json
{
  "scenario_id": "ac_xxxx",
  "prompt_text": "...",
  "response_text": "...",
  "trait_theme": "attention_check",
  "trait_phrase": "attention_check",
  "sentiment": "neutral"
}
```

#### `POST /api/v1/moderation/highlights`
Create a highlight span.

**Request:**
```json
{
  "assignment_id": "uuid",
  "selected_text": "example text",
  "source": "response",
  "start_offset": 10,
  "end_offset": 22
}
```

#### `GET /api/v1/moderation/highlights/{assignment_id}`
Get all highlights for an assignment.

### Admin Endpoints

#### `POST /api/v1/admin/scenarios/upload`
Upload scenarios from JSON file. Always creates new scenarios with UUID-based IDs (never updates existing).

**Request:** Multipart form data
- `file`: JSON file
- `set_name`: Set name (default: "pilot")
- `source`: Source identifier (default: "admin_upload")
- `deactivate_previous`: Boolean (default: false) - If true, deactivates all existing active scenarios with the same `set_name` before uploading

**Response:**
```json
{
  "status": "success",
  "loaded": 45,
  "updated": 0,
  "deactivated_count": 12,
  "errors": 0,
  "total": 45,
  "error_details": []
}
```

**Note:** Uploaded scenarios always get new UUID-based identifiers (`scenario_{uuid}`), so each upload creates entirely new records even if content is identical. Use `deactivate_previous=true` to automatically deactivate previous scenarios with the same set name.

#### `GET /api/v1/admin/scenarios`
List scenarios with filtering and pagination.

**Query Parameters:**
- `is_active`: Filter by active status
- `trait`: Filter by trait
- `polarity`: Filter by polarity
- `domain`: Filter by domain
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50)

#### `GET /api/v1/admin/scenarios/stats`
Get aggregate statistics.

**Response:**
```json
{
  "total_scenarios": 50,
  "active_scenarios": 48,
  "inactive_scenarios": 2,
  "total_assignments": 250,
  "total_completed": 180,
  "total_skipped": 20,
  "total_abandoned": 50
}
```

#### `PATCH /api/v1/admin/scenarios/{scenario_id}`
Update a scenario (e.g., toggle is_active).

**Request:**
```json
{
  "is_active": false
}
```

#### `GET /api/v1/admin/scenarios/set-names`
Get all distinct set_name values for scenarios.

**Response:**
```json
{
  "set_names": ["pilot", "scaled", "v1", null]
}
```

#### `POST /api/v1/admin/scenarios/set-active-set`
Set which set_name should be active. Activates all scenarios with that set_name and deactivates all others.

**Request:**
```json
{
  "set_name": "pilot"  // or null to activate all scenarios
}
```

**Response:**
```json
{
  "status": "success",
  "activated": 45,
  "deactivated": 12,
  "set_name": "pilot"
}
```

#### `POST /api/v1/admin/attention-checks/upload`
Upload attention check scenarios from JSON file. Always creates new attention checks with UUID-based IDs (never updates existing).

**Request:** Multipart form data
- `file`: JSON file
- `set_name`: Set name (default: "default")
- `source`: Source identifier (default: "admin_upload")
- `deactivate_previous`: Boolean (default: false) - If true, deactivates all existing active attention checks with the same `set_name` before uploading

**Response:**
```json
{
  "status": "success",
  "loaded": 10,
  "updated": 0,
  "deactivated_count": 3,
  "errors": 0,
  "total": 10,
  "error_details": []
}
```

**Note:** Uploaded attention checks always get new UUID-based identifiers (`ac_{uuid}`), so each upload creates entirely new records even if content is identical. Use `deactivate_previous=true` to automatically deactivate previous attention checks with the same set name.

#### `GET /api/v1/admin/attention-checks`
List attention check scenarios.

#### `PATCH /api/v1/admin/attention-checks/{scenario_id}`
Update an attention check scenario.

#### `GET /api/v1/admin/attention-checks/set-names`
Get all distinct set_name values for attention checks.

**Response:**
```json
{
  "set_names": ["default", "v1", null]
}
```

#### `POST /api/v1/admin/attention-checks/set-active-set`
Set which set_name should be active. Activates all attention checks with that set_name and deactivates all others.

**Request:**
```json
{
  "set_name": "default"  // or null to activate all attention checks
}
```

**Response:**
```json
{
  "status": "success",
  "activated": 10,
  "deactivated": 3,
  "set_name": "default"
}
```

## Admin Panel Usage

### Accessing Scenario Management

1. Navigate to Admin → Settings → Scenarios tab
2. Use the tabs to switch between "Scenarios" and "Attention Checks"

### Managing Active Sets

The admin panel allows you to control which set of scenarios or attention checks should be active at any given time.

**For Scenarios:**
1. In the "Scenarios" tab, find the "Active Scenario Set" section
2. Select a set name from the dropdown (or "All sets active" to activate everything)
3. Click "Apply Active Set" to activate all scenarios with that set name and deactivate all others

**For Attention Checks:**
1. In the "Attention Checks" tab, find the "Active Attention Check Set" section
2. Select a set name from the dropdown (or "All sets active" to activate everything)
3. Click "Apply Active Set" to activate all attention checks with that set name and deactivate all others

**Note:** The active set selector only controls which scenarios/attention checks are active (`is_active` flag). It does NOT affect scenario selection logic, which already uses `is_active` for filtering. The `set_name` field is only used for:
- Grouping scenarios/attention checks for batch deactivation
- Admin panel filtering and management
- Determining which set should be active

### Uploading Scenarios

1. Enter a **Set Name** (e.g., "pilot", "scaled", "v1") - this groups scenarios together for batch management
2. (Optional) Check "Deactivate previous scenarios with same set name" if you want to deactivate existing scenarios with the same set name before uploading new ones
3. Click "Upload Scenarios JSON" button
4. Select a JSON file matching the format:

**Note:** Uploaded scenarios always get new UUID-based identifiers, so each upload creates entirely new records. If you want to replace old scenarios, use the deactivate checkbox.
   ```json
   [
     {
       "child_prompt": "...",
       "model_response": "...",
       "trait": "Agreeableness",
       "polarity": "positive",
       "prompt_style": "Should I",
       "domain": "Friendship"
     }
   ]
   ```
4. File is processed and scenarios are created with new UUID-based IDs (uploaded scenarios always create new records)
5. Success message shows counts of loaded/deactivated/errors

### Viewing Scenarios

- **Statistics Dashboard**: Shows total, active, assignments, completed counts
- **Filtering**: Use dropdowns to filter by status, trait, polarity, domain
- **Table View**: Shows scenario ID, prompt, response (truncated), metadata, counters, status
- **Pagination**: Navigate through results (50 per page)

### Managing Scenarios

- **Toggle Active Status**: Click "Activate" or "Deactivate" button for any scenario
- **View Counters**: See how many times each scenario has been assigned, completed, skipped, abandoned

### Attention Check Management

Similar interface for managing attention check scenarios:
- Upload JSON files with attention check data (always creates new records with UUID-based IDs)
- Enter a **Set Name** when uploading (e.g., "default", "v1")
- Option to deactivate previous attention checks with same set name before uploading
- Use "Active Attention Check Set" selector to manage which set is active
- View and filter attention checks
- Toggle active status

## Frontend Integration

### Loading Scenarios

The frontend calls `loadRandomScenarios()` which:
1. Checks for restored scenario package in localStorage
2. If not found, calls `/moderation/scenarios/assign` 6 times (SCENARIOS_PER_SESSION)
3. Stores assignment_ids in scenarioStates
4. Calls `/moderation/scenarios/start` when scenario is loaded
5. Persists scenario package to localStorage

### Attention Check Integration

Attention checks are loaded via:
1. Call `GET /moderation/attention-checks/random` API
2. Add instruction suffix to response
3. Shuffle into scenario list (not at position 0 or last)

### Abandonment Detection

- Tracks start time in `scenarioStartTimes` Map
- Sets 30-minute timeout using `abandonmentTimeout`
- On timeout, calls `/abandon` endpoint
- Automatically reassigns if reassignment successful

## Development Guide

### Adding New Scenarios

1. Prepare JSON file with scenario data
2. Use admin panel upload or run script:
   ```bash
   python -m open_webui.scripts.load_scenarios_from_json --json-file path/to/scenarios.json --set-name my_set
   ```

### Modifying Sampling Algorithm

Edit `backend/open_webui/models/scenarios.py`:
- `weighted_sample()` method: Modify weight calculation
- `get_eligible_scenarios()`: Modify eligibility filtering

### Extending Scenario Metadata

1. Add column to `scenarios` table via migration
2. Update `Scenario` model in `models/scenarios.py`
3. Update `ScenarioForm` and `ScenarioModel` Pydantic models
4. Update admin panel UI if needed

### Loading Attention Checks from CSV

The old CSV-based attention check system has been migrated to database. To load from CSV:

1. Convert CSV to JSON format matching attention check structure
2. Use admin panel to upload JSON
3. Or create a script similar to `load_scenarios_from_json.py`

## Testing

See `TESTING_SCENARIO_SELECTION.md` for comprehensive testing procedures.

## Troubleshooting

### "No eligible scenarios available"

**Causes:**
- All scenarios completed/skipped for participant
- No active/validated scenarios in database
- Scenarios not loaded

**Solutions:**
- Check scenario counts: `SELECT COUNT(*) FROM scenarios WHERE is_active=1`
- Load scenarios via admin panel or script
- Reset participant's completed/skipped scenarios if testing

### Weighted sampling seems uneven

**Causes:**
- Alpha parameter too low (less aggressive balancing)
- Pool too small
- Counters not incrementing correctly

**Solutions:**
- Increase alpha parameter (e.g., 2.0 for more aggressive balancing)
- Check that counters increment atomically
- Verify sampling audit fields in assignments table

### Attention checks not loading

**Causes:**
- No active attention checks in database
- API endpoint error
- Authentication token missing

**Solutions:**
- Check attention check counts: `SELECT COUNT(*) FROM attention_check_scenarios WHERE is_active=1`
- Upload attention checks via admin panel
- Check browser console for API errors

## Migration Notes

### From CSV to Database

The system migrated from:
- CSV files (`attention_check_bank.csv`, scenario bank CSV)
- Frontend CSV parsing
- LocalStorage-only scenario storage

To:
- Database tables (`scenarios`, `attention_check_scenarios`)
- Backend API endpoints
- Database-backed assignment tracking

Old CSV files are no longer used. Use admin panel to upload JSON files instead.

