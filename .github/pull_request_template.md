<!--
Important checks for contributors:
1. Target the `dev` branch. PRs targeting `main` will be closed.
2. Code pull requests are not the default contribution path.
3. Do not open a code PR as the first step. Start with a well-written Issue or Discussion unless a maintainer asked for the PR or the change is only i18n/localization.
4. Do not delete the Contributor License Agreement section at the bottom. The CLA bot requires it.
-->

# Pull Request

Thanks for wanting to improve Open WebUI. The most useful contribution is usually a clear, well-written Issue, not an unsolicited code pull request.

Open a code pull request only when a maintainer asks for one, or when the change is only i18n/localization. For real, reproducible bugs, start with a well-described [Issue](https://github.com/open-webui/open-webui/issues). For feature requests, UI/UX changes, behavior changes, architecture changes, suspected fixes, or unconfirmed approaches, start with an active [Discussion](https://github.com/open-webui/open-webui/discussions).

Before continuing, make sure the linked Issue or Discussion explains the user-facing problem, the expected outcome, the affected workflow, and any examples, logs, screenshots, constraints, or reproduction details needed for maintainers to evaluate it.

If you have implementation notes, include them as reference in the Issue or Discussion. If you want to share code as reference, include it there as a local diff, patch, or branch note. Do not open a pull request for reference code.

Unsolicited PRs may be closed without review, especially when they introduce product, architecture, compatibility, dependency, or maintenance decisions that have not been discussed.

## Checklist

- [ ] This PR targets the `dev` branch.
- [ ] This PR links to a well-described, confirmed Issue or active Discussion: `Closes #___` / `Relates to #___`.
- [ ] A maintainer explicitly asked me to open this PR, or this PR only updates i18n/localization.
- [ ] The change is one logical unit with no unrelated commits.
- [ ] I matched nearby code patterns and avoided unnecessary new settings, abstractions, or dependencies.
- [ ] I manually tested the changed workflow and any nearby behavior that could be affected.
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

## Testing

List the exact manual checks you ran. Include commands, setup details, screenshots, or recordings where helpful.

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
