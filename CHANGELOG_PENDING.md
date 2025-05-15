# Pending Changelog

This file tracks all changes made to the repository before they are committed. Do not erase or delete this file; always append new changes and keep version history.

---

## [Unreleased]

### Added
- Documented the need to increase Node.js memory limit (`NODE_OPTIONS=--max-old-space-size=8192`) to prevent heap out of memory errors during Docker or local builds. Added troubleshooting instructions to the README.
- Added a section to the README about faster Docker builds, including enabling BuildKit, Compose Bake, and Dockerfile caching strategies.
- Overwrote .env.example with the version from /home/paulo/open-webui/.env.example to synchronize environment variable examples with the upstream Open WebUI project.

### Changed
- (pending)

### Fixed
- (pending)

### Removed
- (pending) 