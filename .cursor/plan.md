# RAUX Launch Scripts Update Plan

## Overview
We need to update the RAUX launch scripts to remove the conda dependency for Lemonade, which now provides an executable directly via `lemonade-server.bat`. The RAUX conda environment should be preserved.

## Changes Required

### 1. Update launch_raux.cmd
- Remove Lemonade conda environment setting
- Keep only the LAUNCH_LEMONADE flag setting

### 2. Update launch_raux.ps1
- Remove Lemonade conda activation logic
- Update the command to launch Lemonade to use `lemonade-server serve` directly from PATH
- Preserve RAUX conda environment handling

## Tasks

1. [x] Update `launch_raux.cmd` to remove Lemonade conda reference
2. [x] Simplify `launch_raux.cmd` to only handle LAUNCH_LEMONADE flag
3. [x] Modify `launch_raux.ps1` to remove Lemonade conda environment checks
4. [x] Update `launch_raux.ps1` to use `lemonade-server serve` command directly
5. [ ] Test both scripts to ensure they work correctly with the new Lemonade setup
6. [x] Verify RAUX conda environment is still properly used
7. [ ] Document the changes made for future reference