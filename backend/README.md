# Open WebUI Backend

## Running pytests

To run pytests do this:

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. pytest .
```

### VSCode Integration

If you want to run python tests from VSCode, ensure these variables are in the `.vscode/settings.json`:

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.cwd": "${workspaceFolder}/backend"
}
