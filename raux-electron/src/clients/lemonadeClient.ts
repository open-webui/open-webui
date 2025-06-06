import { BaseCliRunner, CliCommandResult, CliCommandOptions } from './baseCliRunner';
import { spawn, ChildProcessWithoutNullStreams } from 'child_process';
import { createServer } from 'net';
import { logInfo, logError } from '../logger';
import { LemonadeHealthCheck } from '../ipc/ipcTypes';

export interface LemonadeVersion {
  full: string;
  major: number;
  minor: number;
  patch: number;
}

export class LemonadeClient extends BaseCliRunner {
  private static instance: LemonadeClient;
  private serverProcess: ChildProcessWithoutNullStreams | null = null;
  private serverStatus: 'starting' | 'running' | 'stopped' | 'crashed' = 'stopped';
  private isStartedByRaux: boolean = false; // Track if RAUX started this process

  private constructor() {
    super('lemonade-server', {
      timeout: 10000,
      shell: true,
      windowsHide: true
    });
  }

  public static getInstance(): LemonadeClient {
    if (!LemonadeClient.instance) {
      LemonadeClient.instance = new LemonadeClient();
    }
    return LemonadeClient.instance;
  }

  /**
   * Get Lemonade version information
   */
  public async getVersion(options: CliCommandOptions = {}): Promise<CliCommandResult & { version?: LemonadeVersion }> {
    logInfo('Getting Lemonade version...');
    
    const result = await this.executeCommand(['--version'], options);

    if (result.success && result.stdout) {
      const version = this.parseVersion(result.stdout);
      return { ...result, version };
    }

    return result;
  }

  /**
   * Check if Lemonade is available
   */
  public async isLemonadeAvailable(options: CliCommandOptions = {}): Promise<boolean> {
    try {
      const result = await this.getVersion({ ...options, timeout: 5000 });
      return result.success && !!result.version;
    } catch {
      return false;
    }
  }

  /**
   * Check Lemonade server health using the Health API
   */
  public async checkHealth(timeoutMs: number = 5000): Promise<LemonadeHealthCheck> {
    const startTime = Date.now();
    
    try {
      const config = this.getLemonadeServerConfig();
      const healthUrl = `http://localhost:${config.port}/api/v0/health`;
      
      // Use fetch with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
      
      const response = await fetch(healthUrl, {
        method: 'GET',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
        },
      });
      
      clearTimeout(timeoutId);
      const responseTime = Date.now() - startTime;
      
      if (response.ok) {
        return {
          isHealthy: true,
          responseTime,
          timestamp: Date.now(),
        };
      }

      return {
        isHealthy: false,
        responseTime,
        error: `HTTP ${response.status}: ${response.statusText}`,
        timestamp: Date.now(),
      };
      
    } catch (error) {
      const responseTime = Date.now() - startTime;
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          return {
            isHealthy: false,
            responseTime,
            error: `Health check timeout after ${timeoutMs}ms`,
            timestamp: Date.now(),
          };
        }
        
        return {
          isHealthy: false,
          responseTime,
          error: error.message,
          timestamp: Date.now(),
        };
      
      }

      return {
        isHealthy: false,
        responseTime,
        error: 'Unknown error during health check',
        timestamp: Date.now(),
      };
    }
  }

  /**
   * Parse version string from Lemonade output
   */
  private parseVersion(output: string): LemonadeVersion | undefined {
    const match = output.match(/([0-9]+)\.([0-9]+)\.([0-9]+)/);
    if (match) {
      const major = parseInt(match[1], 10);
      const minor = parseInt(match[2], 10);
      const patch = parseInt(match[3], 10);
      
      return {
        full: `${major}.${minor}.${patch}`,
        major,
        minor,
        patch
      };
    }
    return undefined;
  }

  /**
   * Start Lemonade server as a managed long-running process
   */
  public async startServerProcess(options: { 
    onStdout?: (data: string) => void;
    onStderr?: (data: string) => void;
    onExit?: (code: number | null) => void;
    envOverrides?: Record<string, string>;
    [key: string]: any;
  } = {}): Promise<{ success: boolean; error?: string }> {
    try {
      // Check if already running
      if (this.serverProcess) {
        logInfo('Lemonade server is already running');
        return { success: true };
      }

      // Verify the command exists before attempting to spawn
      logInfo(`[LemonadeClient] Verifying command exists: ${this.commandName}`);
      const commandExists = await this.isLemonadeAvailable();
      if (!commandExists) {
        const error = `Command '${this.commandName}' not found or not executable`;
        logError(`[LemonadeClient] ${error}`);
        return { success: false, error };
      }

      // Get configuration for port
      const config = this.getLemonadeServerConfig(options.envOverrides || {});
      const args = ['serve', '--port', config.port];
      
      logInfo(`[LemonadeClient] Starting Lemonade server with args: ${args.join(' ')}`);
      logInfo(`[LemonadeClient] Command: ${this.commandName}`);
      logInfo(`[LemonadeClient] Working directory: ${process.cwd()}`);
      logInfo(`[LemonadeClient] PATH: ${process.env.PATH}`);
      this.serverStatus = 'starting';
      
      // Start the lemonade-server with serve command and port
      const spawnOptions = {
        stdio: 'pipe' as const,
        windowsHide: true,
        shell: true, // Required on Windows to find commands in PATH
        env: { ...process.env, ...options.envOverrides }
      };
      
      logInfo(`[LemonadeClient] Spawn options: ${JSON.stringify({ ...spawnOptions, env: Object.keys(spawnOptions.env).length + ' env vars' })}`);
      
      this.serverProcess = spawn(this.commandName, args, spawnOptions);

      // Add immediate error handler before checking PID
      this.serverProcess.on('error', (error: any) => {
        logError(`[LemonadeClient] Spawn error immediately after creation: ${error.message}`);
        logError(`[LemonadeClient] Error code: ${error.code}`);
        logError(`[LemonadeClient] Error errno: ${error.errno}`);
        logError(`[LemonadeClient] Error syscall: ${error.syscall}`);
        logError(`[LemonadeClient] Error path: ${error.path}`);
        logError(`[LemonadeClient] Error spawnfile: ${error.spawnfile}`);
        this.serverStatus = 'crashed';
        this.serverProcess = null;
      });

      // Wait a brief moment for spawn to complete and potential immediate errors
      await new Promise(resolve => setTimeout(resolve, 200));

      if (!this.serverProcess || !this.serverProcess.pid) {
        const error = 'Failed to start Lemonade server process - no PID assigned';
        logError(`[LemonadeClient] ${error}`);
        logError(`[LemonadeClient] serverProcess exists: ${!!this.serverProcess}`);
        logError(`[LemonadeClient] serverProcess.killed: ${this.serverProcess?.killed}`);
        logError(`[LemonadeClient] serverProcess.exitCode: ${this.serverProcess?.exitCode}`);
        logError(`[LemonadeClient] serverProcess.signalCode: ${this.serverProcess?.signalCode}`);
        this.serverStatus = 'crashed';
        this.serverProcess = null;
        return { success: false, error };
      }

      logInfo(`[LemonadeClient] Lemonade server started with PID: ${this.serverProcess.pid}`);
      this.isStartedByRaux = true; // Mark that RAUX started this process

      // Set up event handlers
      this.serverProcess.stdout.on('data', (data) => {
        const output = data.toString();
        logInfo(`[Lemonade][stdout] ${output}`);
        
        // Check if server is ready
        if (this.serverStatus === 'starting' && (output.includes('Running on') || output.includes('Started'))) {
          this.serverStatus = 'running';
        }
        
        if (options.onStdout) {
          options.onStdout(output);
        }
      });

      this.serverProcess.stderr.on('data', (data) => {
        const output = data.toString();
        logError(`[Lemonade][stderr] ${output}`);
        
        if (options.onStderr) {
          options.onStderr(output);
        }
      });

      this.serverProcess.on('close', (code) => {
        logInfo(`Lemonade server process exited with code: ${code}`);
        this.serverStatus = code === 0 ? 'stopped' : 'crashed';
        this.serverProcess = null;
        
        if (options.onExit) {
          options.onExit(code);
        }
      });

      this.serverProcess.on('error', (error) => {
        logError(`Lemonade server process error: ${error.message}`);
        this.serverStatus = 'crashed';
        this.serverProcess = null;
      });

      return { success: true };
    } catch (error) {
      logError(`Failed to start Lemonade server: ${error}`);
      this.serverStatus = 'crashed';
      this.serverProcess = null;
      return { 
        success: false, 
        error: error instanceof Error ? error.message : String(error) 
      };
    }
  }

  /**
   * Stop the managed Lemonade server process using proper stop command
   * Only stops if RAUX started the process
   */
  public async stopServerProcess(): Promise<void> {
    if (!this.isStartedByRaux) {
      logInfo('[LemonadeClient] Lemonade server was not started by RAUX - skipping stop');
      return;
    }

    logInfo('[LemonadeClient] Stopping Lemonade server using stop command (started by RAUX)...');
    
    try {
      // Use the proper lemonade-server stop command
      const result = await this.executeCommand(['stop'], { timeout: 10000 });
      
      if (result.success) {
        logInfo('[LemonadeClient] Lemonade server stopped successfully via stop command');
      } else {
        logError(`[LemonadeClient] Stop command failed: ${result.error || result.stderr}`);
        
        // Fallback to process kill if stop command fails
        if (this.serverProcess) {
          logInfo('[LemonadeClient] Falling back to process termination...');
          this.serverProcess.kill('SIGTERM');
          
          setTimeout(() => {
            if (this.serverProcess) {
              logInfo('[LemonadeClient] Force killing Lemonade server process...');
              this.serverProcess.kill('SIGKILL');
            }
          }, 3000);
        }
      }
    } catch (error) {
      logError(`[LemonadeClient] Error executing stop command: ${error}`);
      
      // Fallback to process kill if stop command throws
      if (this.serverProcess) {
        logInfo('[LemonadeClient] Falling back to process termination...');
        this.serverProcess.kill('SIGTERM');
      }
    }
    
    this.serverStatus = 'stopped';
    this.serverProcess = null;
    this.isStartedByRaux = false;
  }

  /**
   * Get the current server status
   */
  public getServerStatus(): string {
    return this.serverStatus;
  }

  /**
   * Check if the server process is being managed by this client
   */
  public isServerManaged(): boolean {
    return this.serverProcess !== null;
  }

  /**
   * Check if the server was started by RAUX
   */
  public isServerStartedByRaux(): boolean {
    return this.isStartedByRaux;
  }

  /**
   * Legacy method - use startServerProcess for new code
   * @deprecated Use startServerProcess instead
   */
  public async startServer(options: { host?: string; port?: string; [key: string]: any } = {}): Promise<CliCommandResult> {
    logInfo('Warning: startServer is deprecated, use startServerProcess for managed processes');
    
    const config = this.getLemonadeServerConfig();
    const args = ['serve', '--port', options.port || config.port];
    
    logInfo(`Starting Lemonade server with args: ${args.join(' ')}`);
    
    // Start the lemonade-server with serve command and port
    return await this.executeCommand(args, {
      timeout: 60000, // 60 seconds for startup
      ...options
    });
  }

  /**
   * Check if a port is in use
   */
  private async isPortInUse(port: number): Promise<boolean> {
    try {
      return new Promise((resolve) => {
        const server = createServer();
        
        server.listen(port, () => {
          server.close(() => {
            resolve(false); // Port is available
          });
        });
        
        server.on('error', () => {
          resolve(true); // Port is in use
        });
      });
    } catch {
      return true; // Assume port is in use if we can't check
    }
  }

  /**
   * Get Lemonade server configuration with overrides
   */
  public getLemonadeServerConfig(envOverrides: Record<string, string> = {}): Record<string, string> {
    const defaultConfig = {
      host: '0.0.0.0',
      port: '8000'
    };

    return {
      ...defaultConfig,
      host: envOverrides.LEMONADE_HOST || defaultConfig.host,
      port: envOverrides.LEMONADE_PORT || defaultConfig.port,
      // Add other configuration options as needed
    };
  }

  /**
   * Check if a version meets minimum requirements
   */
  public static isVersionCompatible(version: LemonadeVersion, minVersion: LemonadeVersion): boolean {
    if (version.major !== minVersion.major) {
      return version.major >= minVersion.major;
    }
    if (version.minor !== minVersion.minor) {
      return version.minor >= minVersion.minor;
    }
    return version.patch >= minVersion.patch;
  }
}

export const lemonadeClient = LemonadeClient.getInstance();