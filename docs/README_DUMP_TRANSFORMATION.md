# Database Dump Transformation Script

This script transforms PostgreSQL dump files into cleaned pandas DataFrames for analysis.

## Overview

The script `transform_dump_to_dataframes.py` extracts relevant tables from a PostgreSQL dump file and converts them into cleaned, analysis-ready pandas DataFrames.

## Relevant Tables

The script focuses on these tables for analysis:

- **user** - User accounts and profiles
- **chat** - Chat conversations
- **message** - Individual messages
- **child_profile** - Child profile information
- **selection** - Text selections from chats
- **moderation_scenario** - Moderation scenarios
- **moderation_session** - Moderation sessions
- **moderation_applied** - Applied moderation strategies
- **moderation_question_answer** - Moderation Q&A responses
- **exit_quiz_response** - Exit quiz responses
- **scenario_assignments** - Scenario assignments (if present)
- **scenarios** - Scenario definitions (if present)
- **attention_check_scenarios** - Attention check scenarios (if present)
- **assignment_session_activity** - Session activity tracking (if present)

## Requirements

- Python 3.7+
- pandas
- PostgreSQL client tools (for custom format dumps): `pg_restore`

Install dependencies:

```bash
pip install pandas
```

For PostgreSQL custom format dumps, install PostgreSQL client:

- macOS: `brew install postgresql`
- Ubuntu/Debian: `sudo apt-get install postgresql-client`
- Or download from: https://www.postgresql.org/download/

## Usage

### Basic Usage

```bash
python transform_dump_to_dataframes.py [dump_file_path]
```

If no file path is provided, the script will look for:

1. `~/Downloads/b078-20260113-215725.dump`
2. `/workspace/heroku_psql_181025.dump`
3. `./heroku_psql_181025.dump`

### Examples

```bash
# Use specific dump file
python transform_dump_to_dataframes.py ~/Downloads/b078-20260113-215725.dump

# Use default location
python transform_dump_to_dataframes.py
```

## Output

The script creates a `data_exports/` directory with:

- **CSV files**: One per table (e.g., `user.csv`, `chat.csv`)
- **Pickle files**: One per table for faster loading (e.g., `user.pkl`, `chat.pkl`)
- **summary.json**: Metadata about extracted tables

### Loading the DataFrames

```python
import pandas as pd

# Load from pickle (faster)
df_users = pd.read_pickle('data_exports/user.pkl')
df_chats = pd.read_pickle('data_exports/chat.pkl')
df_selections = pd.read_pickle('data_exports/selection.pkl')

# Or load from CSV
df_users = pd.read_csv('data_exports/user.csv')
```

## Data Transformations

The script performs several cleaning and transformation operations:

### Common Transformations (All Tables)

- Converts timestamp columns to datetime objects
- Cleans string columns (removes null bytes, handles 'None' strings)
- Parses JSON fields into Python dictionaries

### Table-Specific Transformations

#### User Table

- Parses `info` and `settings` JSON fields

#### Chat Table

- Parses `chat` JSON field (contains message history)
- Extracts message count from chat history
- Parses `meta` JSON field

#### Message Table

- Parses `data` and `meta` JSON fields

#### Selection Table

- Parses `meta` JSON field

#### Moderation Session Table

- Parses JSON fields: `strategies`, `custom_instructions`, `highlighted_texts`, `refactored_response`, `session_metadata`

#### Exit Quiz Table

- Parses JSON fields: `answers`, `score`, `meta`

## Dump File Formats

The script supports:

1. **PostgreSQL Custom Format** (`.dump`)
   - Detected automatically
   - Requires `pg_restore` to convert to SQL first
   - Script handles conversion automatically

2. **Plain SQL Format** (`.sql`)
   - Can be parsed directly
   - Can be created from custom format:
     ```bash
     pg_restore -f dump.sql your_dump.dump
     ```

## Troubleshooting

### pg_restore not found

If you get an error about `pg_restore` not being available:

1. Install PostgreSQL client tools (see Requirements above)
2. Or manually convert the dump:
   ```bash
   pg_restore -f dump.sql your_dump.dump
   ```
   Then run the script with the SQL file:
   ```bash
   python transform_dump_to_dataframes.py dump.sql
   ```

### Memory Issues

If the dump is very large:

- The script processes tables one at a time
- Consider filtering tables in the `RELEVANT_TABLES` list
- Or use a machine with more RAM

### Encoding Issues

The script handles UTF-8 and Latin-1 encodings. If you encounter encoding errors:

- The script will try to decode with error handling
- Some special characters may be lost

## Example Analysis

After extracting the data:

```python
import pandas as pd

# Load data
users = pd.read_pickle('data_exports/user.pkl')
chats = pd.read_pickle('data_exports/chat.pkl')
selections = pd.read_pickle('data_exports/selection.pkl')

# Basic statistics
print(f"Total users: {len(users)}")
print(f"Total chats: {len(chats)}")
print(f"Total selections: {len(selections)}")

# Users with child profiles
users_with_children = users[users['id'].isin(
    pd.read_pickle('data_exports/child_profile.pkl')['user_id']
)]
print(f"Users with child profiles: {len(users_with_children)}")

# Selections by role
selections_by_role = selections['role'].value_counts()
print(selections_by_role)

# Chats with timestamps
chats['created_at_datetime'] = pd.to_datetime(chats['created_at'], unit='s')
chats_by_date = chats.groupby(chats['created_at_datetime'].dt.date).size()
print(chats_by_date)
```

## Notes

- The script preserves all original columns and adds parsed versions (e.g., `meta_parsed`)
- Timestamp conversions create new columns (e.g., `created_at_datetime`)
- Original data is preserved in case you need to reference it
- Large JSON fields are parsed but original strings are kept
