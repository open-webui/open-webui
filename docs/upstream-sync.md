# Internal Guide: Syncing with Open WebUI (Upstream)

This guide is for the GovGPT engineering team to periodically sync our Azure DevOps repository with the upstream Open WebUI project hosted on GitHub.

## One-Time Setup

These steps are required only once per developer or machine.

1. Clone the internal Azure DevOps repo if not already done:

   ```bash
   git clone https://dev.azure.com/your-org/_git/govgpt-openwebui
   cd govgpt-openwebui
   ```

2. Add the Open WebUI GitHub repository as the upstream remote:

   ```bash
   git remote add upstream https://github.com/open-webui/open-webui.git
   git fetch upstream
   ```

3. Create a local branch that tracks the upstream main branch:
   ```bash
   git checkout -b upstream-main upstream/main
   git push origin upstream-main
   ```

The `upstream-main` branch should be used only to pull updates from GitHub. No development should be done on this branch.

## Periodic Sync Workflow

Use the following steps to update the internal repository when Open WebUI releases new changes:

1. Pull the latest upstream changes:

   ```bash
   git checkout upstream-main
   git pull upstream main
   ```

2. Merge the updates into your main development branch:

   ```bash
   git checkout main
   git merge upstream-main
   ```

3. Resolve any merge conflicts if they appear.

4. Push the updated main branch to Azure DevOps:
   ```bash
   git push origin main
   ```

## Best Practices

- Do not commit or develop directly on `upstream-main`.
- All customizations must be made in `main` or other feature/epic branches.
- Always test and validate functionality after merging upstream changes.
- For large changes, open a PR and request review before merging to `main`.
- Optionally, a scheduled pipeline or GitHub Action can be used to notify the team when new upstream changes are available.

For any questions about this process, reach out to the engineering lead or DevOps owner.
