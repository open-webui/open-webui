import { spawn, ChildProcess } from 'child_process';
import { logInfo, logError } from '../logger';

export interface CliCommandResult {
  success: boolean;
  exitCode: number;
  stdout: string;
  stderr: string;
  error?: string;
}

export interface CliCommandOptions {
  timeout?: number;
  shell?: boolean;
  windowsHide?: boolean;
  cwd?: string;
  env?: Record<string, string>;
}

export abstract class BaseCliRunner {
  protected readonly commandName: string;
  protected readonly defaultOptions: CliCommandOptions;

  constructor(commandName: string, defaultOptions: CliCommandOptions = {}) {
    this.commandName = commandName;
    this.defaultOptions = {
      timeout: 10000, // 10 second default timeout
      shell: true,
      windowsHide: true,
      ...defaultOptions
    };
  }

  /**
   * Execute a CLI command with the given arguments
   * @param args Command arguments
   * @param options Optional command execution options
   * @returns Promise resolving to command result
   */
  protected async executeCommand(args: string[] = [], options: CliCommandOptions = {}): Promise<CliCommandResult> {
    const mergedOptions = { ...this.defaultOptions, ...options };
    
    logInfo(`Executing command: ${this.commandName} ${args.join(' ')}`);

    return new Promise((resolve) => {
      const proc: ChildProcess = spawn(this.commandName, args, {
        shell: mergedOptions.shell,
        timeout: mergedOptions.timeout,
        windowsHide: mergedOptions.windowsHide,
        cwd: mergedOptions.cwd,
        env: { ...process.env, ...mergedOptions.env }
      });

      let stdout = '';
      let stderr = '';
      let timeoutId: NodeJS.Timeout | null = null;

      // Set up timeout handling
      if (mergedOptions.timeout && mergedOptions.timeout > 0) {
        timeoutId = setTimeout(() => {
          proc.kill('SIGTERM');
          resolve({
            success: false,
            exitCode: -1,
            stdout,
            stderr,
            error: `Command timed out after ${mergedOptions.timeout}ms`
          });
        }, mergedOptions.timeout);
      }

      proc.stdout?.on('data', (data) => {
        stdout += data.toString();
      });

      proc.stderr?.on('data', (data) => {
        stderr += data.toString();
      });

      proc.on('error', (error) => {
        if (timeoutId) clearTimeout(timeoutId);
        logError(`Command '${this.commandName}' failed: ${error.message}`);
        resolve({
          success: false,
          exitCode: -1,
          stdout,
          stderr,
          error: error.message
        });
      });

      proc.on('close', (code) => {
        if (timeoutId) clearTimeout(timeoutId);
        
        const result: CliCommandResult = {
          success: code === 0,
          exitCode: code ?? -1,
          stdout: stdout.trim(),
          stderr: stderr.trim()
        };

        if (result.success) {
          logInfo(`Command '${this.commandName}' completed successfully`);
        } else {
          logError(`Command '${this.commandName}' failed with exit code ${code}`);
          if (stderr) {
            logError(`stderr: ${stderr}`);
          }
        }

        resolve(result);
      });
    });
  }

  /**
   * Try multiple command variations (useful for commands that might have different names)
   * @param commandVariations Array of command name variations to try
   * @param args Command arguments
   * @param options Command execution options
   * @returns Promise resolving to first successful result or last failure
   */
  protected async tryCommandVariations(
    commandVariations: string[], 
    args: string[] = [], 
    options: CliCommandOptions = {}
  ): Promise<CliCommandResult> {
    let lastResult: CliCommandResult | null = null;

    for (const variation of commandVariations) {
      const originalCommand = this.commandName;
      // Temporarily change command name for this attempt
      (this as any).commandName = variation;
      
      try {
        const result = await this.executeCommand(args, options);
        
        // Restore original command name
        (this as any).commandName = originalCommand;
        
        if (result.success) {
          logInfo(`Successfully executed with command variation: ${variation}`);
          return result;
        }
        
        lastResult = result;
      } catch (error) {
        // Restore original command name
        (this as any).commandName = originalCommand;
        lastResult = {
          success: false,
          exitCode: -1,
          stdout: '',
          stderr: '',
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }

    return lastResult || {
      success: false,
      exitCode: -1,
      stdout: '',
      stderr: '',
      error: 'All command variations failed'
    };
  }

  /**
   * Check if the command is available in the system
   * @returns Promise resolving to true if command is available
   */
  public async isAvailable(): Promise<boolean> {
    try {
      const result = await this.executeCommand(['--help'], { timeout: 5000 });
      return result.success || result.exitCode === 0;
    } catch {
      return false;
    }
  }

  /**
   * Get the command name being used
   */
  public getCommandName(): string {
    return this.commandName;
  }
}