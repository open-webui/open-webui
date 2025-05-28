import { existsSync, mkdirSync, createWriteStream, rmSync } from 'fs';
import { join } from 'path';
import { getAppInstallDir, getPythonPath } from './envUtils';
import * as os from 'os';
import fetch from 'node-fetch';
import extract from 'extract-zip';
import { spawn } from 'child_process';
import { logInfo, logError } from './logger';
import { IPCManager } from './ipc/ipcManager';
import { IPCChannels } from './ipc/ipcChannels';

const PYTHON_VERSION = '3.11.8';
const PYTHON_DIR = join(getAppInstallDir(), 'python');
const PYTHON_EXE = getPythonPath();

class PythonExec {
  private static instance: PythonExec;
  private constructor() {}
  private ipcManager = IPCManager.getInstance();

  public static getInstance(): PythonExec {
    if (!PythonExec.instance) {
      PythonExec.instance = new PythonExec();
    }
    return PythonExec.instance;
  }

  public getPath(): string {
    return PYTHON_EXE;
  }

  // Verification method for startup flow - no installation messages
  public verifyEnvironment(): boolean {
    try {
      if (!existsSync(PYTHON_DIR)) {
        logInfo('Python environment verification: directory not found');
        return false;
      }
      
      if (!existsSync(PYTHON_EXE)) {
        logInfo('Python environment verification: executable not found');
        return false;
      }
      
      // Quick check that Python is callable
      const { execSync } = require('child_process');
      execSync(`"${PYTHON_EXE}" --version`, {
        encoding: 'utf8',
        timeout: 2000,
        windowsHide: true
      });
      
      logInfo('Python environment verification: passed');
      return true;
    } catch (err) {
      logError(`Python environment verification failed: ${err}`);
      return false;
    }
  }

  public async install(): Promise<void> {
    try {
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Setting up runtime environment...', step: 'python-check' });
      
      if (existsSync(PYTHON_DIR)) {
        logInfo('Python directory already exists, skipping installation.');
        this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'Runtime environment already configured.', step: 'python-check' });
      
        return;
      }
      
      mkdirSync(PYTHON_DIR, { recursive: true });
      
      const url = this.getPythonDownloadUrl();
      const zipPath = join(PYTHON_DIR, 'python-embed.zip');

      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Downloading runtime components...', step: 'python-download' });
      logInfo('Downloading Python from: ' + url);
      await this.downloadPython(url, zipPath);
      
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Extracting runtime libraries...', step: 'python-extract' });
      await this.extractPython(zipPath, PYTHON_DIR);
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Configuring package management...', step: 'pip-install' });
      
      await this.ensurePipInstalled();

      logInfo('Python and pip setup completed successfully.');
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'Runtime environment ready.', step: 'python-complete' });
    } catch (err) {
      logError('Python installation failed: ' + (err && err.toString ? err.toString() : String(err)));
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Runtime environment setup failed!', step: 'python-error' });
      throw err;
    }
  }

  public async runPythonCommand(args: string[], options?: any): Promise<{ code: number, stdout: string, stderr: string }> {
    return this.runCommand(PYTHON_EXE, args, options);
  }

  public async runPipCommand(args: string[], options?: any): Promise<{ code: number, stdout: string, stderr: string }> {
    return this.runCommand(PYTHON_EXE, ['-m', 'pip', ...args], options);
  }

  // --- Private helpers ---

  private getPythonDownloadUrl(): string {
    const arch = os.arch();
    if (arch === 'x64') {
      return `https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip`;
    } else if (arch === 'arm64') {
      return `https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-arm64.zip`;
    } else {
      throw new Error('Unsupported architecture: ' + arch);
    }
  }

  private async downloadPython(url: string, zipPath: string): Promise<void> {
    logInfo('Downloading Python...');
    return new Promise<void>((resolve, reject) => {
      fetch(url)
        .then(response => {
          if (response.status !== 200) {
            logError('Failed to download Python: ' + response.status);
            this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Environment not configurable.', step: 'python-download' });
            reject(new Error('Failed to download Python: ' + response.status));
            return;
          }
          const file = createWriteStream(zipPath);
          response.body.pipe(file);
          file.on('finish', () => {
            file.close();
            logInfo('Python download finished.');
            this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'Runtime components downloaded.', step: 'python-download' });
            resolve();
          });
        })
        .catch(err => {
          logError(`Download error: ${err}`);
          this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Environment download error.', step: 'python-download' });
          reject(err);
        });
    });
  }

  private async extractPython(zipPath: string, destDir: string): Promise<void> {
    logInfo('Extracting Python...');
    try {
      await extract(zipPath, { dir: destDir });
      logInfo('Python extraction finished.');
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'Runtime libraries configured.', step: 'python-extract' });
    } catch (error) {
      logError(`Failed to extract Python: ${error}`);
      this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Failed to extract environment.', step: 'python-extract' });
      throw error;
    }
  }

  private async ensurePipInstalled(): Promise<void> {
    logInfo('Ensuring pip is installed using get-pip.py...');
    const getPipUrl = 'https://bootstrap.pypa.io/get-pip.py';
    const getPipPath = join(PYTHON_DIR, 'get-pip.py');

    this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'info', message: 'Preparing packaging resource...', step: 'pip-download' });

    // Download get-pip.py
    await new Promise<void>((resolve, reject) => {
      fetch(getPipUrl)
        .then(response => {
          if (response.status !== 200) {
            logError('Failed to download get-pip.py: ' + response.status);
            this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Failed to download packaging resource!', step: 'pip-download' });
            reject(new Error('Failed to download get-pip.py: ' + response.status));
            return;
          }
          const file = createWriteStream(getPipPath);
          response.body.pipe(file);
          file.on('finish', () => {
            file.close();
            logInfo('get-pip.py download finished.');
            this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'Packaging resource download finished.', step: 'pip-download' });
            resolve();
          });
        })
        .catch(err => {
          logError(`Download error (get-pip.py): ${err}`);
          this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Packaging resource download error!', step: 'pip-download' });
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
          this.ipcManager.sendToAll(IPCChannels.INSTALLATION_STATUS, { type: 'success', message: 'Packaging resource install success.', step: 'pip-install' });
          resolve();
        } else {
          logError('get-pip.py failed');
          this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Packaging resource failed!', step: 'pip-install' });
          reject(new Error('get-pip.py failed'));
        }
      });
      proc.on('error', (err) => {
        logError(`get-pip.py process error: ${err}`);
        this.ipcManager.sendToAll(IPCChannels.INSTALLATION_ERROR, { type: 'error', message: 'Packaging resource process error.', step: 'pip-install' });
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

  private async runCommand(cmd: string, args: string[], options?: any): Promise<{ code: number, stdout: string, stderr: string }> {
    return new Promise((resolve, reject) => {
      const proc = spawn(cmd, args, { ...options, stdio: ['ignore', 'pipe', 'pipe'] });
      let stdout = '';
      let stderr = '';
      proc.stdout.on('data', (data) => { stdout += data; });
      proc.stderr.on('data', (data) => { stderr += data; });
      proc.on('close', (code) => {
        resolve({ code: code ?? -1, stdout, stderr });
      });
      proc.on('error', (err) => {
        reject(err);
      });
    });
  }
}

export const python = PythonExec.getInstance(); 