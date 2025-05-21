import { app } from 'electron';
import { join, dirname } from 'path';
import os from 'os';

export const isDev = process.env.NODE_ENV === 'development' || process.env.ELECTRON_IS_DEV === '1';

// Directory for app binaries and dependencies (Python, open-webui)
export function getAppInstallDir() {
  if (isDev) {
    // In dev, backend is at ../../backend relative to src
    return join(__dirname, '../../');
  }
  // On Windows, use LOCALAPPDATA env var for AppData\Local
  if (process.platform === 'win32') {
    const localAppData = process.env.LOCALAPPDATA || join(os.homedir(), 'AppData', 'Local');
    return join(localAppData, 'raux');
  }

  return join(app.getPath('appData'), 'raux');
}

// Directory for user data (settings, logs, etc.)
export function getUserInstallDir() {
  if (isDev) {
    return join(__dirname, '../../');
  }
  // In production, use Roaming/raux
  return app.getPath('userData');
}

// Backend directory (open-webui)
export function getBackendDir() {
  if (isDev) {
    return join(__dirname, '../../../backend');
  }
  // Use the resources directory of the running app version
  return dirname(app.getAppPath());
}

// Python executable path
export function getPythonPath() {
  if (isDev) {
    return 'python'; // Use system Python in dev
  }
  return join(getAppInstallDir(), 'python', process.platform === 'win32' ? 'python.exe' : 'bin/python3');
} 