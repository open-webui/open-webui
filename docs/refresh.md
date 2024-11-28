## Reset and Fresh Start Procedure
- [ ] Backup current changes:
  ```bash
  # Create a new branch for current changes
  git checkout -b backup-changes
  git add .
  git commit -m "backup: current state before reset"
  ```
- [ ] Return to main branch and reset:
  ```bash
  # Switch to main branch
  git checkout main
  # Remove all untracked files and directories
  git clean -fd
  # Reset to match remote main
  git fetch origin
  git reset --hard origin/main
  ```
- [ ] Reapply essential changes one by one:
  - [ ] Rename project references:
    1. Update package.json name
    2. Update pyproject.toml name
    3. Update Docker image names
  - [ ] Environment configuration:
    1. Copy .env.example to .env.development
    2. Update essential environment variables
  - [ ] Create fresh virtual environment:
    ```bash
    # Remove existing venv if present
    rm -rf venv
    # Create new virtual environment with Python 3.11
    py -3.11 -m venv venv
    ```
