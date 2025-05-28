// ... existing code ...

# Auto-Launch Prevention Plan

## Overview
Implement a mechanism to prevent RAUX Electron app from automatically launching after installation when installed via GAIA's NSIS installer, while still allowing auto-launch when self-installed.

## Problem Statement
- RAUX should auto-launch after self-installation (default Squirrel installer behavior from Electron Forge)
- RAUX should NOT auto-launch when installed via GAIA's NSIS installer
- Since GAIA (NSIS) invokes RAUX (Squirrel), we need coordination between different installer systems

## Installer Architecture Context
- **GAIA**: Uses NSIS installer (traditional Windows installer)
- **RAUX**: Uses Squirrel installer from Electron Forge (auto-launches by default)
- **Flow**: GAIA NSIS → downloads raux-wheel-context.zip → invokes RAUX Squirrel installer → Squirrel auto-launches app

## Approach
Use a temporary file as a flag to control auto-launch behavior:
1. GAIA NSIS installer creates a flag file in user's temp directory before invoking RAUX Squirrel installer
2. RAUX Squirrel installer installs and auto-launches the app (default Squirrel behavior)
3. RAUX app checks for flag file at startup
4. RAUX removes the file if found and then exits immediately 

## Tasks

### 1. Modify RAUX Electron App
- [x] Add temp file check early in the application lifecycle
- [x] If the flag file exists, exit the application immediately
- [x] Place check before any initialization or window creation
- [x] If the file is found, RAUX will remove it
- [x] RAUX will exit immediately after

### 2. Update GAIA NSIS Installer
- [ ] Add code to create flag file in temp directory before invoking RAUX installer
- [ ] Document this behavior for future maintenance

### 3. Testing
- [ ] Test RAUX self-installation (should auto-launch)
- [ ] Test RAUX installation via NSIS (should not auto-launch)
- [ ] Test manual RAUX launch after NSIS installation (should launch)

## Implementation Details

### RAUX Implementation (COMPLETED)
1. **Location**: `raux-electron/src/envUtils.ts`
   - Created `checkAndHandleAutoLaunchPrevention()` function
   - Checks for `RAUX_PREVENT_AUTOLAUNCH` file in temp directory
   - Removes the file if found
   - Returns true to signal the app should exit

2. **Integration**: `raux-electron/src/index.ts`
   - Calls `checkAndHandleAutoLaunchPrevention()` early (line 23)
   - Exits immediately with `process.exit(0)` if flag detected (line 24)
   - This occurs BEFORE:
     - Any window creation
     - Squirrel event handling
     - Installation processes
     - Any UI initialization

3. **Behavior**:
   - First launch (with flag): Detects → Removes → Exits silently
   - Second launch (no flag): Proceeds normally with installation
   - No windows shown or installation performed when flag is present
