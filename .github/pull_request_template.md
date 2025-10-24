# Pull Request Checklist

### Note to first-time contributors: Please open a discussion post in [Discussions](https://github.com/open-webui/open-webui/discussions) to discuss your idea/fix with the community before creating a pull request, and describe your changes before submitting a pull request.

This is to ensure large feature PRs are discussed with the community first, before starting work on it. If the community does not want this feature or it is not relevant for Open WebUI as a project, it can be identified in the discussion before working on the feature and submitting the PR.

**Before submitting, make sure you've checked the following:**

- [ ] **Target branch:** Verify that the pull request targets the `dev` branch. **Not targeting the `dev` branch will lead to immediate closure of the PR.**
- [ ] **Description:** Provide a concise description of the changes made in this pull request down below.
- [ ] **Changelog:** Ensure a changelog entry following the format of [Keep a Changelog](https://keepachangelog.com/) is added at the bottom of the PR description.
- [ ] **Documentation:** If necessary, update relevant documentation [Open WebUI Docs](https://github.com/open-webui/docs) like environment variables, the tutorials, or other documentation sources.
- [ ] **Dependencies:** Are there any new dependencies? Have you updated the dependency versions in the documentation?
- [ ] **Testing:** Perform manual tests to **verify the implemented fix/feature works as intended AND does not break any other functionality**. Take this as an opportunity to **make screenshots of the feature/fix and include it in the PR description**.
- [ ] **Agentic AI Code:** Confirm this Pull Request is **not written by any AI Agent** or has at least **gone through additional human review AND manual testing**. If any AI Agent is the co-author of this PR, it may lead to immediate closure of the PR.
- [ ] **Code review:** Have you performed a self-review of your code, addressing any coding standard issues and ensuring adherence to the project's coding standards?
- [ ] **Title Prefix:** To clearly categorize this pull request, prefix the pull request title using one of the following:
  - **BREAKING CHANGE**: Significant changes that may affect compatibility
  - **build**: Changes that affect the build system or external dependencies
  - **ci**: Changes to our continuous integration processes or workflows
  - **chore**: Refactor, cleanup, or other non-functional code changes
  - **docs**: Documentation update or addition
  - **feat**: Introduces a new feature or enhancement to the codebase
  - **fix**: Bug fix or error correction
  - **i18n**: Internationalization or localization changes
  - **perf**: Performance improvement
  - **refactor**: Code restructuring for better maintainability, readability, or scalability
  - **style**: Changes that do not affect the meaning of the code (white space, formatting, missing semi-colons, etc.)
  - **test**: Adding missing tests or correcting existing tests
  - **WIP**: Work in progress, a temporary label for incomplete or ongoing work

# Changelog Entry

### Description

- [Concisely describe the changes made in this pull request, including any relevant motivation and impact (e.g., fixing a bug, adding a feature, or improving performance)]

### Added

- [List any new features, functionalities, or additions]

### Changed

- [List any changes, updates, refactorings, or optimizations]

### Deprecated

- [List any deprecated functionality or features that have been removed]

### Removed

- [List any removed features, files, or functionalities]

### Fixed

- [List any fixes, corrections, or bug fixes]

### Security

- [List any new or updated security-related changes, including vulnerability fixes]

### Breaking Changes

- **BREAKING CHANGE**: [List any breaking changes affecting compatibility or functionality]

---

### Additional Information

- [Insert any additional context, notes, or explanations for the changes]
  - [Reference any related issues, commits, or other relevant information]

### Screenshots or Videos

- [Attach any relevant screenshots or videos demonstrating the changes]

### Contributor License Agreement

By submitting this pull request, I confirm that I have read and fully agree to the [Contributor License Agreement (CLA)](https://github.com/open-webui/open-webui/blob/main/CONTRIBUTOR_LICENSE_AGREEMENT), and I am providing my contributions under its terms.

> [!NOTE]
> Deleting the CLA section will lead to immediate closure of your PR and it will not be merged in.
