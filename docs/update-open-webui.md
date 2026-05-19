# Update this Open WebUI fork from upstream safely

Use one of the following methods to keep your fork updated while preserving the upstream fork relationship.

## GitHub UI method

1. Open your fork repository on GitHub.
2. Click **Sync fork**.
3. Click **Update branch**.
4. Review incoming upstream changes.
5. Run the manual Fly deploy GitHub Action after review.

## CLI method

```bash
git remote add upstream https://github.com/open-webui/open-webui.git
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

After updating, trigger the manual deploy workflow to roll out reviewed changes to Fly.io.
