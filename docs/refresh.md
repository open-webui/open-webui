## Reset and Fresh Start Procedure
- [ ] Backup current changes:
  ```bash
  # Create a new branch for current changes
  git checkout -b backup-changes
  git add .
  git commit -m "backup: current state before reset"
  ```

- [x] Document important changes to keep:
  - [x] Project renaming changes:
    - package.json
    - pyproject.toml
    - docker-compose.yaml
  - [x] Documentation:
    - localsetup.md
    - localsetupimplementation.md
    - STRATEGY.md

- [x] Return to main branch and reset:
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
  1. [x] Project renaming:
     ```bash
     # Create a new branch for clean implementation
     git checkout -b clean-implementation
     ```
     - [x] Update package.json name
     - [x] Update pyproject.toml name
     - [x] Update Docker image names
     - [x] Commit these changes:
       ```bash
       git add package.json pyproject.toml docker-compose.yaml
       git commit -m "refactor: rename project to whatever"
       ```
  
  2. [ ] Environment setup:
     - [ ] Copy .env.example to .env.development
     - [ ] Update essential environment variables
     - [ ] Create fresh virtual environment:
       ```bash
       # Remove existing venv if present
       rm -rf venv
       # Create new virtual environment with Python 3.13
       py -3.13 -m venv venv
       ```

## Docker Reset Procedure

If you need to reset your Docker-based development environment:

- [ ] Stop all running containers:
  ```bash
  docker-compose down
  ```
- [ ] Remove all Docker containers and images:
  ```bash
  docker system prune -a
  ```
- [ ] Rebuild and start containers:
  ```bash
  docker-compose up --build -d
  ```

This ensures a clean slate for your Docker environment and resolves any potential issues related to container states or images.
