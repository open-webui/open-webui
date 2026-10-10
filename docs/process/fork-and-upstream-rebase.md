# Fork, local layout and upstream rebase

## Prerequisites

- A GitHub account that owns the `losus-ai` organization (the fork lives there)
- Git installed, and write access to `losus-ai/opencowork-ui`
- On the Spark: the repo added to the `git-guard` allowlist if that wrapper is in use

## Steps

### One-time: local layout and identity

Keep each project in its own folder and keep the parent folder out of git:

```text
~/LosusAI/Projects/losus-ai/
  opencowork-ui/     fork: origin = losus-ai, upstream = open-webui
  <other repos>/     one folder per GitHub repo, same name as the repo
```

Set the commit identity by folder so everything under `~/LosusAI/` uses the Losus address:

```bash
git config \
  --file ~/.gitconfig-losus \
  user.email "mark.susol@losus.ai"
git config \
  --file ~/.gitconfig-losus \
  user.name "Mark Susol"
git config \
  --global \
  "includeIf.gitdir:~/LosusAI/.path" \
  "~/.gitconfig-losus"
```

### One-time: clone and remotes

```bash
git clone https://github.com/losus-ai/opencowork-ui.git
cd opencowork-ui
git remote add upstream https://github.com/open-webui/open-webui.git
git fetch upstream --tags
git fetch origin
git checkout cowork
```

### Branch rules

- `main` mirrors upstream. Never commit to it.
- `cowork` is the product line. Feature work goes on branches such as `cowork/task-inbox` and merges into `cowork`.

### Adopting a new upstream release

1. Fetch the new tag.
2. Rebase `cowork` onto it.
3. Build the image and run the tests.
4. Push `cowork` with a lease, not a plain force.

```bash
git fetch upstream --tags
git checkout cowork
git rebase <new-tag>
git push \
  --force-with-lease \
  origin \
  cowork
```

## Expected output

- `git config user.email`, run inside the repo, prints `mark.susol@losus.ai`
- `git log -1` on `cowork` right after setup shows commit `8bd8b4fac`, tagged `v0.11.4`

## Troubleshooting

- `user.email` still shows a personal address: the rule did not apply. Run `git config --show-origin --get-all user.email` and check that the folder path in the rule matches the clone's real path, including capital letters and the trailing slash.
- `git-guard: ... is not in the allowlist`: the wrapper on the Spark blocks repos that are not approved. Add the repo to its allowlist file, copying the format of the existing entries.
- `error: remote upstream already exists`: harmless if `git remote -v` shows `upstream` pointing at `open-webui/open-webui`.

## Related docs

- [0001. Fork Open WebUI at v0.11.4 into the losus-ai organization](../adr/0001-fork-open-webui-at-v0-11-4.md)
- [Build phases](../plans/build-phases.md)
