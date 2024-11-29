# Deployment Testing Checklist

## 1. Verify Current Setup

### Check Running Environments
- [x] Verify all environments are running:
  ```bash
  docker ps | grep whatever
  ```
  Confirmed running:
  - whatever-prod (80)
  - whatever-dev (3000)
  - whatever-test (3002)
- [x] Confirm endpoints:
  - [x] Production: http://localhost:80
  - [x] Test: http://localhost:3002
  - [x] Development: http://localhost:3000

### Check Branches
- [x] Verify branch structure:
  ```bash
  git branch -a
  ```
- [x] Confirm branches:
  - [x] main (production)
  - [x] test
  - [x] dev

## 2. Configure Branch Rules

### Dev Branch
- [x] Allow direct pushes to dev
- [x] Configure automated tests:
  ```
  - integration-test
  - format-build-frontend
  ```

### Test Branch
- [x] Configure automated merge from dev:
  ```
  - Trigger: All tests pass on dev
  - cypress tests  
  - Automated merge via GitHub Actions
  - No manual pushes allowed
  ```

### Main Branch Protection
- [x] Add rule for 'main':
  ```
  - Require pull request from test
  - All status checks must pass
  - Require manual approval
  - No direct pushes
  ```

## 3. Configure Automated Workflows

### Dev to Test Workflow
- [x] Create/verify GitHub Action:
  ```yaml
  name: Dev to Test Merge
  on:
    push:
      branches: [dev]
    workflow_run:
      workflows: ["Integration Test"]
      types:
        - completed
  
  jobs:
    verify-tests:
      if: ${{ github.event.workflow_run.conclusion == 'success' }}
      # ...rest of the workflow
  ```

## 4. Test Development Workflow

### Make a Test Change
- [ ] Create feature branch (optional):
  ```bash
  git checkout dev
  git pull
  git checkout -b feature/test-change  # optional
  ```
- [ ] Make a visible UI change
- [ ] Test locally:
  ```bash
  # View changes at http://localhost:3000
  ```
- [ ] Push to dev:
  ```bash
  git commit -am "test: visible UI change"
  git push origin dev  # or push feature branch and merge to dev
  ```

### Verify Automated Flow
- [ ] Watch GitHub Actions:
  - [ ] Tests running on dev
  - [ ] Cypress tests running on test
  - [ ] Automated merge to test
  - [ ] Test environment deployment
- [ ] Verify changes propagate:
  ```bash
  # Should automatically appear at http://localhost:3002
  ```

## 5. Test Production Deploy

### Production Deployment
- [ ] Create PR from test to main
- [ ] Verify all checks passed
- [ ] Get manual deployment approval
- [ ] Merge to production
- [ ] Verify in production:
  ```bash
  # Check http://localhost:80
  ```

## 6. Verify Complete Flow

### Final Checks
- [ ] Change visible in all environments:
  - [ ] Dev (3000)
  - [ ] Test (3002) - automatically deployed
  - [ ] Prod (80)
- [ ] Automation working:
  - [ ] Can push to dev
  - [ ] Tests run automatically
  - [ ] Cypress tests run on test
  - [ ] Auto-merge to test when all tests pass
  - [ ] No direct pushes to test possible
  - [ ] Main requires manual approval
- [ ] All workflows functioning:
  - [ ] integration-test
  - [ ] format-build-frontend
  - [ ] cypress tests
  - [ ] auto-merge workflow