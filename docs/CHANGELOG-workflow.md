# CHANGELOG of GitHub Actions Workflow and Tests

## 2024-08-12

### Added

- For `integration-test.yml` enable github actions on all branches:

  ```
  on:
  push:
      branches:
              - '*'
  ```

- For `integration-test.yml`, added env under `Cypress run`:

  ```
  env:
      SKIP_OLLAMA_TESTS: 'true'
  ```

- For `cypress/e2e/chat.cy.ts`, added env condition `SKIP_OLLAMA_TESTS`.
- Added env `SKIP_OLLAMA_TESTS` in `cypress.config.ts`:

  ```
  env:{
          SKIP_OLLAMA_TESTS: false
  }
  ```

- Updated version to `0.3.13` in `package.json`

### Removed

- Commented out jobs `Wait for Ollama to be up` and `Preload Ollama model` in `integration-test.yml`
- Disabled `Release to PyPI` workflow
- Formatted `backend/apps/images/main.py`
