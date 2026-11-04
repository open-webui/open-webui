# Updating BatchTechUI

## Get told about new versions
On the GitHub repo, click **Watch**, then **Custom**, tick **Releases**, and **Apply**. GitHub emails you when a new
version is published. (The in-app "update available" popup is off: it only knows about Open WebUI's own releases.)

## Upgrade
1. **Back up first.** BatchTechUI migrates its database forward on start and cannot always go back.
   Copy your data volume or run your backup script.
2. In your clone of the repo:
   ```bash
   git pull
   git checkout v<version>          # the release you want, or stay on main for the newest
   docker build -t batchtechui:latest .
   docker rm -f batchtechui
   docker run -d --name batchtechui <the same options you used before> batchtechui:latest
   ```
   Keep the same data volume and port options you used the first time.
3. Open the site, hard-refresh the page, and check **Settings, About** for the new version.

## Rolling back
Run the previous version's image again (`git checkout v<old>`, rebuild). If the new version already changed your
database, restore the backup from step 1 first.

## For the person releasing
Merge the work to `main` with `BATCHTECH_VERSION` bumped in `backend/open_webui/utils/batchtech_version.py`, then
GitHub, Actions, **Release BatchTechUI**, Run workflow, and type what changed.
