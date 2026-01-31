# Quick Start: Transform Database Dump to DataFrames

## Prerequisites

1. **Activate your conda environment:**

   ```bash
   conda activate open-webui
   ```

2. **Install required packages:**

   ```bash
   pip install pandas jupyter ipython
   ```

3. **Install PostgreSQL client tools** (for custom format dumps):

   ```bash
   # macOS
   brew install postgresql

   # Ubuntu/Debian
   sudo apt-get install postgresql-client
   ```

## Option 1: Use Jupyter Notebook (Recommended)

1. **Start Jupyter:**

   ```bash
   jupyter notebook data_cleaning_notebook.ipynb
   ```

2. **Run all cells** - The notebook will:
   - Find and verify the dump file
   - Convert custom format to SQL (if needed)
   - Parse all tables
   - Clean and transform the data
   - Save cleaned DataFrames to `data_exports/`

## Option 2: Use Python Script

1. **Convert dump to SQL** (if custom format):

   ```bash
   pg_restore -f dump.sql ~/Downloads/b078-20260113-215725.dump
   ```

2. **Run transformation script:**
   ```bash
   python transform_dump_to_dataframes.py dump.sql
   ```

## Output

All cleaned data will be saved to `data_exports/`:

- `*.csv` files for each table
- `*.pkl` files (faster loading)
- `summary.json` with metadata

## Load Cleaned Data

```python
import pandas as pd

# Load from pickle (faster)
df_users = pd.read_pickle('data_exports/users.pkl')
df_chats = pd.read_pickle('data_exports/chats.pkl')
df_selections = pd.read_pickle('data_exports/selections.pkl')

# Or from CSV
df_users = pd.read_csv('data_exports/users.csv')
```

## Troubleshooting

### pg_restore not found

- Install PostgreSQL client tools (see Prerequisites)
- Or convert manually: `pg_restore -f dump.sql your_dump.dump`

### Dump file not found

- Place dump file in one of these locations:
  - `~/Downloads/b078-20260113-215725.dump`
  - `/workspace/heroku_psql_181025.dump`
  - Or provide path as argument

### Import errors

- Make sure conda environment is activated
- Install missing packages: `pip install pandas jupyter`
