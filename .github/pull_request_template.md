## What & why

<!-- One paragraph. Link the issue/ticket if there is one. -->

## Tests

<!-- Required. See docs/architecture/testing.md -->

- [ ] New/changed behaviour is covered by an **integration test** hitting the real
      endpoint against a real DB (`backend/tests/`), or — for a pure frontend change —
      by a vitest unit test on extracted logic in `lib/utils/`
- [ ] New pure functions have unit tests
- [ ] `pytest` passes locally
- [ ] `npm run test:frontend` and `npm run check` pass
- [ ] If coverage was not possible, it's explained below

<!-- If you couldn't cover something, say what and why: -->

## Checks

- [ ] Conventional commit title, scoped by domain — e.g. `feat(knowledge): …`
- [ ] `ruff format` / `prettier` clean
- [ ] New code follows the layering in `docs/architecture/` (thin router → service →
      repository; components split rather than grown)
- [ ] Touched upstream (non-knowledge) code minimally, to keep future merges cheap
- [ ] New UI strings added to `src/lib/i18n` + `npm run i18n:parse` run

## Notes

<!-- Migrations, config/env changes, screenshots, anything a reviewer should know. -->
