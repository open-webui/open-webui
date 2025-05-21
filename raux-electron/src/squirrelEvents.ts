import { app } from 'electron';
import { getAppInstallDir, getUserInstallDir } from './envUtils';
import { rauxProcessManager } from './rauxProcessManager';
import { rmSync, readFileSync, writeFileSync, existsSync } from 'fs';
import { spawn } from 'child_process';
import { logInfo } from './logger';
import * as path from 'path';

function cleanupRauxInstallation(): void {
  try {
    logInfo('Attempting to kill RAUX processes...');
    rauxProcessManager.stopRaux();
  } catch (e) {
    // Ignore errors
  }
  
  try {
    const installDir = getAppInstallDir();
    const userDir = getUserInstallDir();
    console.log('Removing install dir:', installDir);
    rmSync(installDir, { recursive: true, force: true });
    console.log('Removing user dir:', userDir);
    rmSync(userDir, { recursive: true, force: true });
    app.quit();
  } catch (e) {
    // Ignore errors
  }
}

/**
 * Ensures the embedded Python environment can find installed packages like pip and setuptools.
 *
 * This function patches the python311._pth file in the embedded Python directory to add
 * 'Lib\\site-packages' and an empty line at the end (enabling import site). This is required
 * because the embeddable Python distribution on Windows uses python311._pth to control sys.path.
 * Without this, Python will not find site-packages or pip, even if they exist on disk.
 *
 * Should be called after Python extraction during install/update events.
 *
 * @param {string} pythonDir - The path to the embedded Python directory.
 */
function patchPythonPthFile(pythonDir: string): void {
  const pthPath = path.join(pythonDir, 'python311._pth');
  if (!existsSync(pthPath)) return;
  let content = readFileSync(pthPath, 'utf-8');
  if (!content.includes('Lib\\site-packages')) {
    content += '\nLib\\site-packages\n\n';
    writeFileSync(pthPath, content, 'utf-8');
  } else if (!content.endsWith('\n\n')) {
    // Ensure there's an empty line at the end to enable import site
    content += '\n';
    writeFileSync(pthPath, content, 'utf-8');
  }
}

function createDesktopShortcut(updateExe: any, exeName: string): void {
  // Patch python311._pth after extraction (in case Python was just installed)
  const pythonDir = path.resolve(getAppInstallDir(), 'python');
  patchPythonPthFile(pythonDir);
  try {
    spawn(updateExe, ['--createShortcut', exeName], { detached: true });
  } catch (e) {
    // Ignore errors
  }
  app.quit();
}

/**
 * Handles Squirrel events for Electron (Windows install/uninstall/update hooks).
 * Returns true if a Squirrel event was handled and the app should exit.
 */
export function handleSquirrelEvent(): boolean {
  if (process.platform !== 'win32') return false;
  const squirrelEvent = process.argv[1];
  const exeName = 'raux.exe';
  const updateExe = path.resolve(process.execPath, '..', '..', 'Update.exe');
  switch (squirrelEvent) {
    case '--squirrel-uninstall':
      cleanupRauxInstallation();
      return true;
    case '--squirrel-install':
    case '--squirrel-updated':
      createDesktopShortcut(updateExe, exeName);
      return true;
    case '--squirrel-obsolete':
      app.quit();
      return true;
    default:
      // Not a Squirrel event, do not quit, just return false
      return false;
  }
}