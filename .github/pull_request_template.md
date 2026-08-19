<!--
⚠️ CRITICAL CHECKS FOR CONTRIBUTORS (READ, DON'T DELETE) ⚠️
1. Target the `dev` branch. PRs targeting `main` will be automatically closed.
2. First-time contributors should not open pull requests directly unless the pull request contains only i18n/localization updates.
   Do not open a PR as the first step.
   For real, reproducible bugs, start with a well-described Issue that explains the problem, why it matters, and what outcome you are looking for.
   For feature requests, enhancements, behavior changes, UI/UX changes, architecture changes, suspected fixes, or unconfirmed approaches, start with an active Discussion.
   If you want to propose an implementation, include it only as a reference in the Issue or Discussion, such as a local diff, patch, or branch.
   Opening an Issue or Discussion does not mean a PR is the right next step. Maintainers will confirm when a PR would be useful.
   We ask for this because PRs, especially from first-time contributors, often need broader maintainer context on product direction, scope, architecture, UX, edge cases, compatibility, documentation, and long-term maintenance before implementation.
   We may close unsolicited PRs without review.
   Contributors with a history of successful merged PRs may be given more latitude.
3. Do NOT delete the CLA section at the bottom. It is required for the bot to accept your PR.
-->

# Pull Request Checklist

### Do not open a pull request as the first step.

For real, reproducible bugs, start with a well-described [Issue](https://github.com/open-webui/open-webui/issues) that explains the problem, why it matters, and what outcome you are looking for.

For feature requests, enhancements, behavior changes, UI/UX changes, architecture changes, suspected fixes, or unconfirmed approaches, start with an active [Discussion](https://github.com/open-webui/open-webui/discussions). Merely opening a discussion is not enough; it needs to be actively discussed.

If you want to propose an implementation, include it only as a reference in the Issue or Discussion, such as a local diff, patch, or branch.

Opening an Issue or Discussion does not mean a PR is the right next step. Maintainers will confirm when a PR would be useful.

We ask for this because PRs, especially from first-time contributors, often need broader maintainer context on product direction, scope, architecture, UX, edge cases, compatibility, documentation, and long-term maintenance before implementation.

Unsolicited PRs may be closed without review. Contributors with a history of successful merged PRs may be given more latitude.

<!--
### ⚠️ Important: Your PR is a contribution, not a guarantee of merge.

We appreciate thoughtful contributions. Pull requests are for implementation-ready changes that have already been requested, confirmed, or actively discussed in a linked Issue or Discussion. Feature ideas, behavior changes, UI/UX changes, architecture changes, suspected fixes, and unconfirmed approaches should start as an Issue or Discussion instead.

Before opening a PR, make sure the change has a clear linked problem, follows nearby patterns, has been manually tested, and accounts for related or downstream behavior. PRs that are ideas, prototypes, unresolved design questions, unchecked AI-generated code, symptom-only patches, one-off patches, or changes where affected paths have not been checked will usually be closed.

The most impactful way to contribute to Open WebUI is through well-written bug reports, detailed feature discussions, and thoughtful ideas. These directly shape the project. If you do open a pull request, please know that Open WebUI is held to the highest standard of code quality, consistency, and architectural coherence, and every line merged becomes something the core team must own, maintain, and support indefinitely. Submitted code may be refactored, rewritten, or used as inspiration for a different implementation. This is not a reflection of your work's quality. It is how we ensure that a small team can deeply understand and evolve every part of the codebase.
-->

**Before submitting, make sure you've checked and filled out the following:**

- [ ] **Linked Issue/Discussion:** This PR references an existing, well-described [Issue](https://github.com/open-webui/open-webui/issues) for a real bug or an active, substantive [Discussion](https://github.com/open-webui/open-webui/discussions) for a feature request or enhancement — `Closes #___` / `Relates to #___`.
- [ ] **First-time contributor policy:** This is not my first contribution to Open WebUI, this PR contains only i18n/localization updates, or a maintainer explicitly asked me to open this PR after reviewing the linked Issue or Discussion.
- [ ] **Target branch:** The pull request targets the `dev` branch. **PRs targeting `main` will be immediately closed.**
- [ ] **Description:** A concise description of the changes is provided below.
- [ ] **Changelog:** A changelog entry following [Keep a Changelog](https://keepachangelog.com/) format is included at the bottom.
- [ ] **Documentation:** Relevant documentation has been added or updated in the [Open WebUI Docs Repository](https://github.com/open-webui/docs).
- [ ] **Dependencies:** Any new or updated dependencies are explained, tested, and documented.
- [ ] **Testing:** **Manual** end-to-end tests have been performed to verify the fix/feature works correctly and does not introduce regressions. Screenshots or recordings are included where applicable.
- [ ] **User-facing changes:** I have confirmed whether this PR changes the UI. If it does, screenshots are required, and a video recording is recommended.
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

- [Attach screenshots or videos for user-facing changes. For UI changes, screenshots are required, and a video recording is recommended.]

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
