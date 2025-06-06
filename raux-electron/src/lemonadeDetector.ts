import { lemonadeClient, LemonadeVersion } from './clients/lemonadeClient';
import { logInfo, logError } from './logger';

export interface LemonadeInfo {
  isAvailable: boolean;
  version?: LemonadeVersion;
  error?: string;
}

export class LemonadeDetector {
  private static instance: LemonadeDetector;
  private cachedInfo: LemonadeInfo | null = null;

  private constructor() {}

  public static getInstance(): LemonadeDetector {
    if (!LemonadeDetector.instance) {
      LemonadeDetector.instance = new LemonadeDetector();
    }
    return LemonadeDetector.instance;
  }

  /**
   * Checks if Lemonade is available and gets its version.
   * This serves as both an existence check and version check.
   */
  public async checkLemonade(forceRefresh: boolean = false): Promise<LemonadeInfo> {
    if (!forceRefresh && this.cachedInfo) {
      logInfo('Using cached Lemonade detection result');
      return this.cachedInfo;
    }

    logInfo('Checking for Lemonade availability and version...');
    
    try {
      const result = await lemonadeClient.getVersion();
      
      if (result.success && result.version) {
        this.cachedInfo = {
          isAvailable: true,
          version: result.version
        };
        logInfo(`Lemonade detected: version ${result.version.full}`);
      } else {
        this.cachedInfo = {
          isAvailable: false,
          error: result.error || 'Lemonade not found'
        };
        logInfo('Lemonade not detected');
      }
      
      return this.cachedInfo;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      this.cachedInfo = {
        isAvailable: false,
        error: errorMessage
      };
      logError(`Error checking Lemonade: ${errorMessage}`);
      return this.cachedInfo;
    }
  }

  /**
   * Clear cached detection result
   */
  public clearCache(): void {
    this.cachedInfo = null;
  }
}

export const lemonadeDetector = LemonadeDetector.getInstance();