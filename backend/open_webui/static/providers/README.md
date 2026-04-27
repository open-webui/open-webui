# Provider logos

SVG logos used as default profile images for models when no
`meta.profile_image_url` is configured (see
`open_webui.utils.models.provider_logos`).

## Source and license

The icons are sourced from [lobehub/lobe-icons][1], licensed under the MIT
License (see `LICENSE` in this directory). They are vendored here rather than
fetched from a CDN so that:

- the UI works offline / in air-gapped deployments,
- there is no third-party request leaking model identifiers,
- the asset pipeline is fully reproducible.

[1]: https://github.com/lobehub/lobe-icons

## Updating

Files are upstream `@lobehub/icons-static-svg` packages. To refresh, replace
the relevant `*.svg` with the latest version from
`https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/<slug>.svg`.

## Adding a new provider

1. Drop `<slug>.svg` (or `<slug>-color.svg`) into this directory.
2. Add a regex rule to `backend/open_webui/utils/models/provider_logos.py`.
3. Add a row to the test matrix in
   `backend/open_webui/test/util/test_provider_logos.py`.
