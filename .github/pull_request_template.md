<!--
⚠️ CRITICAL CHECKS FOR CONTRIBUTORS (READ, DON'T DELETE) ⚠️
1. Target the `dev` branch. PRs targeting `main` will be automatically closed.
2. Do NOT delete the CLA section at the bottom. It is required for the bot to accept your PR.
-->

# Pull Request Checklist

### Note to first-time contributors: Please open a discussion post in [Discussions](https://github.com/open-webui/open-webui/discussions) to discuss your idea/fix with the community before creating a pull request, and describe your changes before submitting a pull request.

This is to ensure large feature PRs are discussed with the community first, before starting work on it. If the community does not want this feature or it is not relevant for Open WebUI as a project, it can be identified in the discussion before working on the feature and submitting the PR.

<!--
### ⚠️ Important: Your PR is a contribution, not a guarantee of merge.

The most impactful way to contribute to Open WebUI is through well-written bug reports, detailed feature discussions, and thoughtful ideas. These directly shape the project. If you do open a pull request, please know that Open WebUI is held to the highest standard of code quality, consistency, and architectural coherence, and every line merged becomes something the core team must own, maintain, and support indefinitely. Submitted code may be refactored, rewritten, or used as inspiration for a different implementation. This is not a reflection of your work's quality. It is how we ensure that a small team can deeply understand and evolve every part of the codebase.
-->

**Before submitting, make sure you've checked the following:**

- [ ] **Linked Issue/Discussion:** This PR references an existing [Issue](https://github.com/open-webui/open-webui/issues) or [Discussion](https://github.com/open-webui/open-webui/discussions) — `Closes #___` / `Relates to #___`. If one does not exist, create one first. PRs without a linked issue or discussion may be closed without review.
- [ ] **Target branch:** The pull request targets the `dev` branch. **PRs targeting `main` will be immediately closed.**
- [ ] **Description:** A concise description of the changes is provided below.
- [ ] **Changelog:** A changelog entry following [Keep a Changelog](https://keepachangelog.com/) format is included at the bottom.
- [ ] **Documentation:** Relevant documentation has been added or updated in the [Open WebUI Docs Repository](https://github.com/open-webui/docs).
- [ ] **Dependencies:** Any new or updated dependencies are explained, tested, and documented.
- [ ] **Testing:** Manual tests have been performed to verify the fix/feature works correctly and does not introduce regressions. Screenshots or recordings are included where applicable.
- [ ] **No Unchecked AI Code:** This PR is either human-written or has undergone thorough human review AND manual testing. Unreviewed AI-generated PRs may be closed immediately.
- [ ] **Self-Review:** A self-review of the code has been performed, ensuring adherence to project coding standards.
- [ ] **Architecture:** Smart defaults are preferred over new settings. Local state is used for ephemeral UI logic. Major architectural or UX changes have been discussed first.
- [ ] **Git Hygiene:** The PR is atomic (one logical change), rebased on `dev`, and contains no unrelated commits.
- [ ] **Title Prefix:** The PR title uses one of the following prefixes:
  - **BREAKING CHANGE**: Changes affecting backward compatibility
  - **build**: Build system or dependency changes
  - **ci**: CI/CD workflow changes
  - **chore**: Refactoring, cleanup, or non-functional changes
  - **docs**: Documentation additions or updates
  - **feat**: New features or enhancements
  - **fix**: Bug fixes or corrections
  - **i18n**: Internationalization or localization changes
  - **perf**: Performance improvements
  - **refactor**: Code restructuring
  - **style**: Formatting changes (whitespace, semicolons, etc.)
  - **test**: Test additions or corrections
  - **WIP**: Work in progress

# Changelog Entry

### Description

- [Describe the changes, including motivation and impact]

### Added

- [New features, functionalities, or additions]

### Changed

- [Changes, updates, refactorings, or optimizations]

### Deprecated

- [Deprecated functionality or features]

### Removed

- [Removed features, files, or functionalities]

### Fixed

- [Bug fixes or corrections]

### Security

- [Security-related changes or vulnerability fixes]

### Breaking Changes

- **BREAKING CHANGE**: [Changes affecting compatibility or functionality]

---

### Additional Information

- [Any additional context, notes, or references to related issues/commits]

### Screenshots or Videos

- [Attach relevant screenshots or videos demonstrating the changes]

### Contributor License Agreement

<!--
🚨 DO NOT DELETE THE TEXT BELOW 🚨
Keep the "Contributor License Agreement" confirmation text intact.
Deleting it will trigger the CLA-Bot to INVALIDATE your PR.

Your PR will NOT be reviewed or merged until you check the box below confirming that you have read and agree to the terms of the CLA.
-->

- [ ] By submitting this pull request, I confirm that I have read and fully agree to the [Contributor License Agreement (CLA)](https://github.com/open-webui/open-webui/blob/main/CONTRIBUTOR_LICENSE_AGREEMENT), and I am providing my contributions under its terms.

> [!NOTE]
> Deleting the CLA section will lead to immediate closure of your PR and it will not be merged in.
