<!--
Important checks for contributors:
1. DO NOT OPEN A CODE PULL REQUEST unless a maintainer explicitly asked you to, or the change is strictly limited to i18n/localization.
2. Target the `dev` branch. PRs targeting `main` will be closed.
3. Do not delete the Contributor License Agreement section at the bottom. The CLA bot requires it.
-->

# Pull Request

**Do not open a code pull request unless a maintainer has explicitly requested it or the change is limited to i18n/localization.**

The most useful way to help is to give us a clear understanding of the problem: report reproducible bugs in [Issues](https://github.com/open-webui/open-webui/issues) and share proposals in [Discussions](https://github.com/open-webui/open-webui/discussions). We use that context to evaluate solutions and refine the implementation internally, accounting for the broader codebase and ongoing work. External implementations usually require substantial reworking to fit the project's standards, and coordinating those revisions usually takes more effort than developing the solution internally. Please follow this process before investing time in a pull request. PRs opened outside these guidelines are generally closed without review.

## Maintainer Request

Link the maintainer's request for this PR, or state that the change is limited to i18n/localization.

## Checklist

- [ ] I have read and I understand the [contribution policy](https://docs.openwebui.com/contributing/#submit-code).
- [ ] This PR targets the `dev` branch.
- [ ] This PR links to a well-described, confirmed Issue or active Discussion: `Closes #___` / `Relates to #___`.
- [ ] A maintainer explicitly asked me to open this PR, or this PR only updates i18n/localization.
- [ ] The change is one logical unit with no unrelated commits.
- [ ] I matched nearby code patterns and avoided unnecessary new settings, abstractions, or dependencies.
- [ ] I manually tested the changed workflow and any nearby behavior that could be affected.
- [ ] I have not added or rewritten automated tests, fixtures, snapshots, or testing infrastructure unless a maintainer explicitly requested them.
- [ ] I updated relevant docs, including the [Open WebUI Docs Repository](https://github.com/open-webui/docs), if needed.
- [ ] I added screenshots for UI changes, and a recording when motion or interaction matters.
- [ ] I reviewed any AI-generated code before submitting it.
- [ ] The PR title uses one of the prefixes listed below.

## Title Prefix

Use one of the following prefixes:

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

## Summary

Describe the change, the problem it solves, and the impact on users.

## Verification

Describe how you reproduced the problem and manually checked the behavior before and after the change. Include exact steps, setup details, and relevant logs, screenshots, or recordings. Report results from relevant existing checks and anything you could not verify.

Do not add or rewrite automated tests unless a maintainer explicitly requests them. Tests that repeat an implementation's assumptions can pass while preserving the same mistake; maintainers determine the regression coverage needed. Do not remove, disable, or weaken existing tests to make the change pass.

## Changelog Entry

### Added

-

### Changed

-

### Fixed

-

### Removed

-

### Security

-

### Breaking Changes

-

## Additional Context

Add anything maintainers should know before review.

## Contributor License Agreement

<!--
DO NOT DELETE THIS SECTION.
Your PR will not be reviewed or merged until you check the box below confirming that you have read and agree to the CLA.
-->

- [ ] By submitting this pull request, I confirm that I have read and fully agree to the [Contributor License Agreement (CLA)](https://github.com/open-webui/open-webui/blob/main/CONTRIBUTOR_LICENSE_AGREEMENT), and I am providing my contributions under its terms.
