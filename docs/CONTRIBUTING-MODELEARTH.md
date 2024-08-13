# Contributing to MODEL.EARTH Open WebUI Project

1. **Branching from Main**: Always create a new branch when introducing new features. Avoid editing directly on the main branch to ensure the stability of the project.

2. **Version Updates**: Don’t forget to update the _version number_ when adding new features to the main branch. Failure to do so will cause the `build_release` workflow to fail.

3. **Frontend Formatting**: Before pushing changes to the frontend code, run `npm run format` and `npm run i18n:parse` to ensure proper formatting. Add your own tests under `./cypress/e2e/`, start the server, and run `npx cypress run` to execute the test suites. Ensure all tests pass without errors.

4. **Backend Formatting**: For any backend changes, run `npm run format:backend` to maintain code formatting. Add any necessary tests to ensure your code changes are covered.

5. **Pull Requests Merging**: After creating a pull request, fill in the template and wait for all workflows to execute. Address any issues if a workflow fails before merging into the main branch.
