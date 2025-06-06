import { existsSync, appendFileSync, openSync } from 'fs';
import { join } from 'path';
import { request } from 'http';
import { getAppInstallDir } from './envUtils';
import { logInfo, logError } from './logger';
import { lemonadeClient } from './clients/lemonadeClient';

class LemonadeProcessManager {
  private static readonly MAX_RESTART_ATTEMPTS = 3;
  private static readonly HEALTH_CHECK_INTERVAL_MS = 30000; // 30 seconds
  private static readonly STARTUP_TIMEOUT_MS = 30000; // 30 seconds
  private static readonly HEALTH_CHECK_TIMEOUT_MS = 2000; // 2 seconds
  private static readonly RESTART_DELAY_MS = 5000; // 5 seconds

  private logPath: string;
  private restartAttempts = 0;
  private healthCheckInterval: NodeJS.Timeout | null = null;

  constructor() {
    const installDir = getAppInstallDir();
    this.logPath = join(installDir, 'lemonade.log');
    
    logInfo(`[LemonadeProcessManager] installDir: ${installDir}`);
    logInfo(`[LemonadeProcessManager] logPath: ${this.logPath}`);
  }

  async isLemonadeAvailable(): Promise<boolean> {
    return await lemonadeClient.isLemonadeAvailable();
  }


  async isLemonadeRunning(): Promise<boolean> {
    // Check if Lemonade server is already running by trying to connect to its port
    try {
      const config = lemonadeClient.getLemonadeServerConfig();
      return new Promise((resolve) => {
        const options = {
          hostname: 'localhost',
          port: parseInt(config.port, 10),
          path: '/api/v0/health',
          method: 'GET',
          timeout: LemonadeProcessManager.HEALTH_CHECK_TIMEOUT_MS
        };

        const req = request(options, (res) => {
          resolve(res.statusCode === 200);
        });

        req.on('error', (err) => {
          logInfo(`[LemonadeProcessManager] Health check error: ${err.message}`);
          resolve(false);
        });
        req.on('timeout', () => {
          req.destroy();
          logInfo('[LemonadeProcessManager] Health check timeout');
          resolve(false);
        });

        req.end();
      });
    } catch (err) {
      logError(`[LemonadeProcessManager] Health check exception: ${err}`);
      return false;
    }
  }

  async startLemonade(envOverrides: Record<string, string> = {}) {
    try {
      // Check if Lemonade is available
      if (!await this.isLemonadeAvailable()) {
        logInfo('[LemonadeProcessManager] Lemonade not available on system');
        return false;
      }

      // Check if already running
      if (await this.isLemonadeRunning()) {
        logInfo('[LemonadeProcessManager] Lemonade already running externally');
        return true;
      }


      logInfo('[LemonadeProcessManager] Starting Lemonade server...');
      
      // Ensure log file exists
      if (!existsSync(this.logPath)) openSync(this.logPath, 'w');

      // Configure server options
      const serverOptions = {
        envOverrides,
        onStdout: (data: string) => {
          appendFileSync(this.logPath, data);
          logInfo(`[LemonadeProcessManager][stdout] ${data.trim()}`);
        },
        onStderr: (data: string) => {
          appendFileSync(this.logPath, data);
          logError(`[LemonadeProcessManager][stderr] ${data.trim()}`);
        },
        onExit: (code: number | null) => {
          appendFileSync(this.logPath, `\nLemonade process exited with code ${code}\n`);
          logError(`[LemonadeProcessManager] Lemonade process exited with code ${code}`);
          this.stopHealthCheck();

          // Auto-restart if crashed and under max attempts
          if (code !== 0 && this.restartAttempts < LemonadeProcessManager.MAX_RESTART_ATTEMPTS) {
            this.restartAttempts++;
            logInfo(`[LemonadeProcessManager] Attempting restart ${this.restartAttempts}/${LemonadeProcessManager.MAX_RESTART_ATTEMPTS}`);
            setTimeout(() => this.startLemonade(envOverrides), LemonadeProcessManager.RESTART_DELAY_MS);
          }
        }
      };

      // Start the server using lemonadeClient
      const result = await lemonadeClient.startServerProcess(serverOptions);
      
      if (!result.success) {
        logError(`[LemonadeProcessManager] Failed to start Lemonade: ${result.error}`);
        return false;
      }

      // Wait for server to be ready (with timeout)
      const startTime = Date.now();
      
      while ((Date.now() - startTime) < LemonadeProcessManager.STARTUP_TIMEOUT_MS) {
        const status = lemonadeClient.getServerStatus();
        
        if (status === 'running') {
          this.restartAttempts = 0;
          this.startHealthCheck();
          logInfo('[LemonadeProcessManager] Lemonade server is ready');
          return true;
        }
        
        if (status === 'crashed') {
          logError('[LemonadeProcessManager] Lemonade server crashed during startup');
          return false;
        }
        
        // Also check if server is responding via HTTP
        if (await this.isLemonadeRunning()) {
          this.restartAttempts = 0;
          this.startHealthCheck();
          logInfo('[LemonadeProcessManager] Lemonade server is responding');
          return true;
        }
        
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      logError('[LemonadeProcessManager] Lemonade failed to start within timeout');
      this.stopLemonade();
      return false;
    } catch (err) {
      logError(`[LemonadeProcessManager] Error starting Lemonade: ${err && err.toString ? err.toString() : String(err)}`);
      return false;
    }
  }

  private startHealthCheck() {
    if (this.healthCheckInterval) return;

    this.healthCheckInterval = setInterval(async () => {
      if (lemonadeClient.getServerStatus() === 'running' && !lemonadeClient.isServerManaged()) {
        // We think it's running but we don't have a process - check if it's running externally
        if (!await this.isLemonadeRunning()) {
          logError('[LemonadeProcessManager] Lemonade health check failed - server not responding');
          this.stopHealthCheck();
        }
      }
    }, LemonadeProcessManager.HEALTH_CHECK_INTERVAL_MS);
  }

  private stopHealthCheck() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }

  async stopLemonade() {
    this.stopHealthCheck();
    await lemonadeClient.stopServerProcess();
  }

  getStatus() {
    return lemonadeClient.getServerStatus();
  }

  isManaged(): boolean {
    return lemonadeClient.isServerManaged();
  }

  getLemonadeConfig(): Record<string, string> {
    return lemonadeClient.getLemonadeServerConfig();
  }

  isStartedByRaux(): boolean {
    return lemonadeClient.isServerStartedByRaux();
  }

  async getInfo(): Promise<{ 
    status: string; 
    isManaged: boolean; 
    isRunning: boolean; 
    isAvailable: boolean;
    isStartedByRaux: boolean;
    config: Record<string, string>;
  }> {
    return {
      status: this.getStatus(),
      isManaged: this.isManaged(),
      isRunning: await this.isLemonadeRunning(),
      isAvailable: await this.isLemonadeAvailable(),
      isStartedByRaux: this.isStartedByRaux(),
      config: this.getLemonadeConfig(),
    };
  }
}

export const lemonadeProcessManager = new LemonadeProcessManager();