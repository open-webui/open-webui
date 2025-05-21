# Plan for Implementing Separate Environment Configurations for RAUX

## Current State
- Single environment file `raux.env` used for all builds
- Single packaging job `package-windows` in the GitHub Action workflow
- The job copies `raux.env` to `backend\.env` during build

## Goals
- Split configuration into separate environment files for different deployment scenarios
- Create separate build jobs to produce distinct installers
- Maintain Windows compatibility throughout the build pipeline

## Tasks

### 1. Create Separate Environment Files
- [x] Create `raux-generic.env` based on current `raux.env` but remove `OPENAI_API_BASE_URLS` line
- [x] Create `raux-hybrid.env` based on current `raux.env` (keeping `OPENAI_API_BASE_URLS` line)

### 2. Modify GitHub Action Workflow
- [x] Duplicate the existing `package-windows` job to create:
  - `package-generic` job
  - `package-hybrid` job
- [x] Modify the "Setup RAUX Environment" step in each job:
  - In `package-generic`: copy `raux-generic.env` to `.env`
  - In `package-hybrid`: copy `raux-hybrid.env` to `.env`
- [x] Update the "Rename installer to raux-setup.exe" section name to "Rename installer"
  - In the "hybrid" version, it will create an "exe" named "raux-hybrid-setup.exe"
  - In the "generic" version, it will create an "exe" named "raux-generic-setup.exe"
- [x] Add appropriate output artifact naming to distinguish between builds
- [x] Update any dependencies between jobs as necessary

### 3. Testing
- [ ] Validate workflow runs successfully
- [ ] Confirm both installers are generated correctly with the right configurations
- [ ] Verify the electron app reads the environment variables correctly

## Implementation Notes
- Use Windows-compatible commands in the GitHub Actions
- Ensure all paths use appropriate Windows path separators (`\`) where needed
- Consider artifact naming conventions to clearly identify generic vs. hybrid builds
