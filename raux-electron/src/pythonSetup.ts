import { existsSync, mkdirSync, createWriteStream, rmSync } from 'fs';
import { join } from 'path';
import { getAppInstallDir, getPythonPath } from './envUtils';
import * as os from 'os';
import fetch from 'node-fetch';
import extract from 'extract-zip';
import { spawn } from 'child_process';
import { logInfo, logError } from './logger';

const PYTHON_VERSION = '3.11.8';
const PYTHON_DIR = join(getAppInstallDir(), 'python');
const PYTHON_EXE = getPythonPath();

function getPythonDownloadUrl() {
  const arch = os.arch();
  if (arch === 'x64') {
    return `https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip`;
  } else if (arch === 'arm64') {
    return `https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-arm64.zip`;
  } else {
    throw new Error('Unsupported architecture: ' + arch);
  }
}

async function downloadPython(url: string, zipPath: string) {
  logInfo('Downloading Python...');
  return new Promise<void>((resolve, reject) => {
    fetch(url)
      .then(response => {
        if (response.status !== 200) {
          logError('Failed to download Python: ' + response.status);
          reject(new Error('Failed to download Python: ' + response.status));
          return;
        }
        const file = createWriteStream(zipPath);
        response.body.pipe(file);
        file.on('finish', () => {
          file.close();
          logInfo('Python download finished.');
          resolve();
        });
      })
      .catch(err => {
        logError(`Download error: ${err}`);
        reject(err);
      });
  });
}

async function extractPython(zipPath: string, destDir: string) {
  logInfo('Extracting Python...');
  try {
    await extract(zipPath, { dir: destDir });
    logInfo('Python extraction finished.');
  } catch (error) {
    logError(`Failed to extract Python: ${error}`);
    throw error;
  }
}

async function ensurePipInstalled() {
  logInfo('Ensuring pip is installed using get-pip.py...');
  const getPipUrl = 'https://bootstrap.pypa.io/get-pip.py';
  const getPipPath = join(PYTHON_DIR, 'get-pip.py');

  // Download get-pip.py
  await new Promise<void>((resolve, reject) => {
    fetch(getPipUrl)
      .then(response => {
        if (response.status !== 200) {
          logError('Failed to download get-pip.py: ' + response.status);
          reject(new Error('Failed to download get-pip.py: ' + response.status));
          return;
        }
        const file = createWriteStream(getPipPath);
        response.body.pipe(file);
        file.on('finish', () => {
          file.close();
          logInfo('get-pip.py download finished.');
          resolve();
        });
      })
      .catch(err => {
        logError(`Download error (get-pip.py): ${err}`);
        reject(err);
      });
  });

  // Run get-pip.py
  await new Promise<void>((resolve, reject) => {
    const proc = spawn(PYTHON_EXE, [getPipPath, '--no-warn-script-location'], { stdio: 'pipe' });

    proc.stdout.on('data', (data) => logInfo(`[get-pip.py][stdout] ${data}`));
    proc.stderr.on('data', (data) => logError(`[get-pip.py][stderr] ${data}`));
    
    proc.on('close', (code) => {
      if (code === 0) {
        logInfo('pip installed successfully via get-pip.py.');
        resolve();
      } else {
        logError('get-pip.py failed');
        reject(new Error('get-pip.py failed'));
      }
    });
    proc.on('error', (err) => {
      logError(`get-pip.py process error: ${err}`);
      reject(err);
    });
  });

  // Clean up get-pip.py
  try {
    rmSync(getPipPath, { force: true });
    logInfo('get-pip.py deleted after pip installation.');
  } catch (err) {
    logError(`Failed to delete get-pip.py: ${err}`);
  }

  // Patch python311._pth to include Lib and Lib\site-packages
  try {
    const fs = await import('fs');
    const path = await import('path');
    // Find the ._pth file (e.g., python311._pth)
    const files = fs.readdirSync(PYTHON_DIR);
    const pthFile = files.find(f => /^python\d+\d+\._pth$/.test(f));
    
    if (!pthFile) {
      logError('No python*._pth file found to patch.');
      return;
    }

    const pthPath = path.join(PYTHON_DIR, pthFile);
    let content = fs.readFileSync(pthPath, 'utf-8');
    let changed = false;
    if (!content.match(/^Lib\s*$/m)) {
      content += '\nLib\n';
      changed = true;
    }
    if (!content.match(/^Lib\\site-packages\s*$/m)) {
      content += 'Lib\\site-packages\n';
      changed = true;
    }
    if (changed) {
      fs.writeFileSync(pthPath, content, 'utf-8');
      logInfo(`Patched ${pthFile} to include Lib and Lib\\site-packages.`);
    } else {
      logInfo(`${pthFile} already includes Lib and Lib\\site-packages.`);
    }

  } catch (err) {
    logError(`Failed to patch python*._pth: ${err}`);
  }
}

async function downloadRAUXWheel(): Promise<string> {
  logInfo('Downloading RAUX build context zip...');
  const wheelDir = join(getAppInstallDir(), 'wheels');

  mkdirSync(wheelDir, { recursive: true });

  // Get the version directly from the environment variable defined by webpack
  const rauxVersion = process.env.RAUX_VERSION || 'latest';
  logInfo(`Using RAUX version: ${rauxVersion}`);

  // Construct URL for the zip file
  let zipUrl: string;
  if (rauxVersion === 'latest') {
    zipUrl = process.env.RAUX_WHEEL_URL || 'https://github.com/aigdat/raux/releases/latest/download/raux-wheel-context.zip';
  } else {
    // Remove the 'v' prefix if present for consistent URL formatting
    const versionStr = rauxVersion.startsWith('v') ? rauxVersion.substring(1) : rauxVersion;
    zipUrl = process.env.RAUX_WHEEL_URL || 
             `https://github.com/aigdat/raux/releases/download/v${versionStr}/raux-wheel-context.zip`;
  }

  logInfo(`Downloading build context zip from URL: ${zipUrl}`);

  // Download the zip file to a temp directory
  const tmpDir = join(wheelDir, `tmp-${Date.now()}`);
  mkdirSync(tmpDir, { recursive: true });
  const zipPath = join(tmpDir, 'raux-build-context.zip');

  await new Promise<void>((resolve, reject) => {
    fetch(zipUrl)
      .then(response => {
        if (response.status !== 200) {
          logError('Failed to download build context zip: ' + response.status);
          reject(new Error('Failed to download build context zip: ' + response.status));
          return;
        }
        const file = createWriteStream(zipPath);
        response.body.pipe(file);
        file.on('finish', () => {
          file.close();
          logInfo('Build context zip download finished.');
          resolve();
        });
      })
      .catch(err => {
        logError(`Build context zip download error: ${err}`);
        reject(err);
      });
  });

  // Extract the zip file
  logInfo('Extracting build context zip...');

  try {
    await extract(zipPath, { dir: tmpDir });
    logInfo('Build context extraction finished.');
  } catch (error) {
    logError(`Failed to extract build context zip: ${error}`);
    throw error;
  }

  // Return the temp directory path
  return tmpDir;
}

async function installRAUXWheel(extractDir: string): Promise<void> {
  logInfo(`Installing RAUX wheel(s) from directory: ${extractDir}...`);
  const fs = await import('fs');
  const path = await import('path');
  const whlFiles = fs.readdirSync(extractDir).filter(f => f.endsWith('.whl'));
  if (whlFiles.length === 0) {
    logError('No .whl files found in extracted build context.');
    throw new Error('No .whl files found in extracted build context.');
  }
  for (const whlFile of whlFiles) {
    const wheelPath = path.join(extractDir, whlFile);
    await new Promise<void>((resolve, reject) => {
      const proc = spawn(PYTHON_EXE, ['-m', 'pip', 'install', wheelPath, '--verbose', '--no-warn-script-location'], {
        stdio: 'pipe'
      });
      proc.stdout.on('data', (data) => logInfo(`[wheel-install][stdout] ${data}`));
      proc.stderr.on('data', (data) => logError(`[wheel-install][stderr] ${data}`));
      proc.on('close', (code) => {
        if (code === 0) {
          logInfo(`${whlFile} installed successfully.`);
          resolve();
        } else {
          logError(`Failed to install ${whlFile}. Exit code: ${code}`);
          reject(new Error(`Failed to install ${whlFile}. Exit code: ${code}`));
        }
      });
      proc.on('error', (err) => {
        logError(`Wheel installation process error: ${err}`);
        reject(err);
      });
    });
  }
}

export async function ensurePythonAndPipInstalled() {
  let tmpDir: string | null = null;
  try {
    // If PYTHON_DIR exists, assume setup is complete and skip installation
    if (existsSync(PYTHON_DIR)) {
      logInfo('Python directory already exists, skipping installation.');
      return;
    }
    // Remove PYTHON_DIR if it exists, then recreate it
    if (existsSync(PYTHON_DIR)) {
      rmSync(PYTHON_DIR, { recursive: true, force: true });
    }
    
    mkdirSync(PYTHON_DIR, { recursive: true });
    const url = getPythonDownloadUrl();
    const zipPath = join(PYTHON_DIR, 'python-embed.zip');
    await downloadPython(url, zipPath);
    await extractPython(zipPath, PYTHON_DIR);
    await ensurePipInstalled();
    
    // Download and install RAUX wheel before installing other requirements
    try {
      tmpDir = await downloadRAUXWheel();
      await installRAUXWheel(tmpDir);
      logInfo('RAUX wheel setup completed successfully.');
    } catch (wheelError) {
      logError(`RAUX wheel installation failed: ${wheelError}`);
      logError('Falling back to requirements.txt installation...');
      // Continue with requirements.txt as fallback
    }

    // Copy raux.env to python/Lib/.env (always overwrite)
    await copyEnvToPythonLib(tmpDir);
    
    // Remove the temp directory after copyEnvToPythonLib
    if (tmpDir) {
      try {
        rmSync(tmpDir, { recursive: true, force: true });
        logInfo(`Temporary directory ${tmpDir} removed.`);
      } catch (err) {
        logError(`Failed to remove temporary directory ${tmpDir}: ${err}`);
      }
    }

    logInfo('Python and pip setup completed successfully.');
  } catch (err) {
    logError(`ensurePythonAndPipInstalled failed: ${err}`);
    throw err;
  }
}

// Copy raux.env from Electron resources to python/Lib/.env, always overwriting
async function copyEnvToPythonLib(extractDir: string) {
  try {
    if (process.platform !== 'win32') {
      logError('copyEnvToPythonLib: Only supported on Windows.');
      return;
    }
    // Check GAIA_MODE first
    const gaiaMode = process.env.GAIA_MODE;
    let envFileName: string;
    
    if (gaiaMode !== undefined) {
      if (gaiaMode === 'HYBRID') {
        envFileName = 'raux-hybrid.env';
      } else {
        envFileName = 'raux-generic.env';
      }
    } else {
      // Fallback to lemonade_server path-based check
      const pathEnv = process.env.PATH || '';
      const userProfile = process.env.USERPROFILE || '';
      const hasLemonade = pathEnv.includes('lemonade_server') || userProfile.includes('lemonade_server');
      envFileName = hasLemonade ? 'raux-hybrid.env' : 'raux-generic.env';
    }

    const srcEnv = join(extractDir, envFileName);
    const destEnv = join(PYTHON_DIR, 'Lib', '.env');
    if (!existsSync(srcEnv)) {
      logError(`copyEnvToPythonLib: Source ${envFileName} not found at ${srcEnv}`);
      return;
    }

    // Ensure Lib directory exists
    const libDir = join(PYTHON_DIR, 'Lib');
    if (!existsSync(libDir)) {
      mkdirSync(libDir, { recursive: true });
    }

    const fs = await import('fs');
    fs.copyFileSync(srcEnv, destEnv);
    logInfo(`Copied ${envFileName} to ${destEnv}`);
  } catch (err) {
    logError(`copyEnvToPythonLib failed: ${err}`);
  }
} 