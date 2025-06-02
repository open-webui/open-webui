import { mkdirSync, existsSync, rmSync } from 'fs';
import { join } from 'path';
import fetch from 'node-fetch';
import extract from 'extract-zip';
import { python } from './pythonExec';
import { getAppInstallDir } from './envUtils';
import { logInfo, logError } from './logger';
import { IPCManager } from './ipc/ipcManager';
import { IPCChannels } from './ipc/ipcChannels';

class RauxSetup {
  private static instance: RauxSetup;
  private static readonly RAUX_HYBRID_ENV = 'raux-hybrid.env';
  private static readonly RAUX_GENERIC_ENV = 'raux-generic.env';
  private constructor() {}
  private ipcManager = IPCManager.getInstance();

  public static getInstance(): RauxSetup {
    if (!RauxSetup.instance) {
      RauxSetup.instance = new RauxSetup();
    }
    return RauxSetup.instance;
  }

  public isRAUXInstalled(): boolean {
    try {
      logInfo('Checking if RAUX is already installed...');
      
      // Check if .env file exists
      const envFile = join(getAppInstallDir(), 'python', 'Lib', '.env');
      if (!existsSync(envFile)) {
        logInfo(`RAUX env file not found at: ${envFile}`);
        return false;
      }
      logInfo(`RAUX env file found at: ${envFile}`);

      // Check if open-webui executable exists
      logInfo('Checking if open-webui executable exists...');
      const { execSync } = require('child_process');
      const openWebuiPath = join(getAppInstallDir(), 'python', 'Scripts', 'open-webui.exe');
      if (!existsSync(openWebuiPath)) {
        logInfo(`open-webui executable not found at: ${openWebuiPath}`);
        return false;
      }
      
      // Try to run it with --help to verify it's functional
      execSync(`"${openWebuiPath}" --help`, {
        encoding: 'utf8',
        timeout: 2000,
        windowsHide: true
      });
      
      logInfo('RAUX installation verified successfully');
      return true;
    } catch (err) {
      logError(`RAUX installation check failed: ${err}`);
      return false;
    }
  }

  // Verification method for startup flow - no installation messages
  public verifyInstallation(): boolean {
    try {
      // Check if .env file exists
      const envFile = join(getAppInstallDir(), 'python', 'Lib', '.env');
      if (!existsSync(envFile)) {
        logInfo('RAUX verification: env file not found');
        return false;
      }

      // Quick check if open-webui executable is available
      const { execSync } = require('child_process');
      const openWebuiPath = join(getAppInstallDir(), 'python', 'Scripts', 'open-webui.exe');
      if (!existsSync(openWebuiPath)) {
        logInfo('RAUX verification: executable not found');
        return false;
      }
      
      execSync(`"${openWebuiPath}" --help`, {
        encoding: 'utf8',
        timeout: 2000,
        windowsHide: true
      });
      
      logInfo('RAUX verification: passed');
      return true;
    } catch (err) {
      logError(`RAUX verification failed: ${err}`);
      return false;
    }
  }

  public async install(): Promise<void> {
    // Check if RAUX is already installed
    if (this.isRAUXInstalled()) {
      logInfo('RAUX installation already exists and is functional, skipping installation.');
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'GAIA Beta components already installed.', step: 'raux-check' });
      return;
    }

    let tmpDir: string | null = null;
    try {
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Downloading GAIA Beta components...', step: 'raux-download' });
      tmpDir = await this.downloadRAUXWheel();
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Installing GAIA Beta...', step: 'raux-install' });
      await this.installRAUXWheel(tmpDir);
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Configuring GAIA Beta environment...', step: 'raux-env' });
      await this.copyEnvToPythonLib(tmpDir);
      if (tmpDir) {
        try {
          rmSync(tmpDir, { recursive: true, force: true });
          logInfo(`Temporary directory ${tmpDir} removed.`);
        } catch (err) {
          logError(`Failed to remove temporary directory ${tmpDir}: ${err}`);
        }
      }
      logInfo('RAUX wheel and env setup completed successfully.');
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_COMPLETE, { type: 'success', message: 'GAIA Beta installation completed.', step: 'raux-complete' });
    } catch (err) {
      logError(`RAUX wheel installation failed: ${err}`);
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'GAIA Beta installation failed!', step: 'raux-error' });
      throw err;
    }
  }

  private async downloadRAUXWheel(): Promise<string> {
    logInfo('Downloading RAUX build context zip...');
    const wheelDir = join(getAppInstallDir(), 'wheels');
    mkdirSync(wheelDir, { recursive: true });
    const rauxVersion = process.env.RAUX_VERSION || 'latest';
    logInfo(`Using RAUX version: ${rauxVersion}`);
    let zipUrl: string;
    if (rauxVersion === 'latest') {
      zipUrl = process.env.RAUX_WHEEL_URL || 'https://github.com/aigdat/raux/releases/latest/download/raux-wheel-context.zip';
    } else {
      const versionStr = rauxVersion.startsWith('v') ? rauxVersion.substring(1) : rauxVersion;
      zipUrl = process.env.RAUX_WHEEL_URL || 
               `https://github.com/aigdat/raux/releases/download/v${versionStr}/raux-wheel-context.zip`;
    }
    logInfo(`Downloading build context zip from URL: ${zipUrl}`);
    const tmpDir = join(wheelDir, `tmp-${Date.now()}`);
    mkdirSync(tmpDir, { recursive: true });
    const zipPath = join(tmpDir, 'raux-build-context.zip');
    // Simple retry logic - try up to 3 times
    const maxAttempts = 3;
    let lastError: Error | null = null;
    
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        await new Promise<void>((resolve, reject) => {
          fetch(zipUrl)
            .then(response => {
              if (response.status !== 200) {
                logError('Failed to download build context zip: ' + response.status);
                reject(new Error('Failed to download build context zip: ' + response.status));
                return;
              }
              const file = require('fs').createWriteStream(zipPath);
              response.body.pipe(file);
              file.on('finish', () => {
                file.close();
                logInfo('Build context zip download finished.');
                this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'GAIA Beta components downloaded.', step: 'raux-download' });
                resolve();
              });
            })
            .catch(err => {
              logError(`Build context zip download error: ${err}`);
              reject(err);
            });
        });
        // Success - exit the retry loop
        lastError = null;
        break;
      } catch (err) {
        lastError = err as Error;
        if (attempt < maxAttempts) {
          logInfo(`Download failed, retrying... (attempt ${attempt + 1}/${maxAttempts})`);
          await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds before retry
        }
      }
    }
    
    if (lastError) {
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Failed to download GAIA environment.', step: 'raux-download' });
      throw lastError;
    }
    logInfo('Extracting build context zip...');
    try {
      await extract(zipPath, { dir: tmpDir });
      logInfo('Build context extraction finished.');
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'GAIA Beta components extracted.', step: 'raux-extract' });
    } catch (error) {
      logError(`Failed to extract build context zip: ${error}`);
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Failed to extract GAIA environment.', step: 'raux-extract' });
      throw error;
    }
    return tmpDir;
  }

  private async installRAUXWheel(extractDir: string): Promise<void> {
    logInfo(`Installing RAUX wheel(s) from directory: ${extractDir}...`);
    this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Preparing GAIA Beta installation...', step: 'raux-env' });
    
    const fs = require('fs');
    const path = require('path');
    const whlFiles = fs.readdirSync(extractDir).filter((f: string) => f.endsWith('.whl'));
    
    if (whlFiles.length === 0) {
      logError('No .whl files found in extracted build context.');
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Installation package not found.', step: 'raux-install' });
      throw new Error('No .whl files found in extracted build context.');
    }

    this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Installing components!', step: 'raux-env' });
    this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Install may take 5 to 10 minutes...', step: 'raux-env' });
    
    for (const whlFile of whlFiles) {
      const wheelPath = path.join(extractDir, whlFile);

      // Use app-specific cache directory to avoid permission issues
      const pipCacheDir = path.join(getAppInstallDir(), 'python', 'pip-cache');
      mkdirSync(pipCacheDir, { recursive: true });
      
      const result = await python.runPipCommand(['install', wheelPath, '--cache-dir', pipCacheDir, '--verbose', '--no-warn-script-location']);
      
      if (result.code === 0) {
        logInfo(`${whlFile} installed successfully.`);
        this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'GAIA Beta components installed successfully.', step: 'raux-install' });
      } else {
        logError(`Failed to install ${whlFile}. Exit code: ${result.code}`);
        if (result.stderr) {
          logError(`pip stderr output:\n${result.stderr}`);
        }
        if (result.stdout) {
          logError(`pip stdout output:\n${result.stdout}`);
        }
        this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Failed to install GAIA environment.', step: 'raux-install' });
        throw new Error(`Failed to install ${whlFile}. Exit code: ${result.code}\nError: ${result.stderr}`);
      }
    }
  }

  private async copyEnvToPythonLib(extractDir: string): Promise<void> {
    try {
      if (process.platform !== 'win32') {
        logError('copyEnvToPythonLib: Only supported on Windows.');

        this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'GAIA environment only supported on Windows.', step: 'raux-env' });

        return;
      }

      const gaiaMode = process.env.GAIA_MODE;
      let envFileName: string;

      if (gaiaMode !== undefined) {
        if (gaiaMode === 'HYBRID') {
          envFileName = RauxSetup.RAUX_HYBRID_ENV;
        } else {
          envFileName = RauxSetup.RAUX_GENERIC_ENV;
        }
      } else {
        this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Setting GAIA mode ...', step: 'raux-env' });
        const pathEnv = process.env.PATH || '';
        const userProfile = process.env.USERPROFILE || '';
        const hasLemonade = pathEnv.includes('lemonade_server') || userProfile.includes('lemonade_server');
        envFileName = hasLemonade ? RauxSetup.RAUX_HYBRID_ENV : RauxSetup.RAUX_GENERIC_ENV;
        this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: `GAIA mode set to ${envFileName}.`, step: 'raux-env' });
      }

      const srcEnv = join(extractDir, envFileName);
      const destEnv = join(getAppInstallDir(), 'python', 'Lib', '.env');

      if (!existsSync(srcEnv)) {
        logError(`copyEnvToPythonLib: Source ${envFileName} not found at ${srcEnv}`);
        this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'GAIA environment not found.', step: 'raux-env' });
        return;
      }

      const libDir = join(getAppInstallDir(), 'python', 'Lib');
      if (!existsSync(libDir)) {
        mkdirSync(libDir, { recursive: true });
      }

      require('fs').copyFileSync(srcEnv, destEnv);
      logInfo(`Copied ${envFileName} to ${destEnv}`);
      
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'GAIA Beta configuration completed.', step: 'raux-env' });
    } catch (err) {
      logError(`copyEnvToPythonLib failed: ${err}`);
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'GAIA environment configuration failed.', step: 'raux-env' });
    }
  }
}

export const raux = RauxSetup.getInstance(); 