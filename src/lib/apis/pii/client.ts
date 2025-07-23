import { config } from '$lib/stores';
import { get } from 'svelte/store';
import type { 
  PiiEntity, 
  KnownPiiEntity, 
  PiiMaskResponse, 
  PiiUnmaskResponse, 
  PiiSession,
  ShieldApiModifier 
} from './index';

// Configuration interface for the PII API client
export interface PiiApiClientConfig {
  apiKey: string;
  baseUrl?: string;
  retryAttempts?: number;
  retryDelay?: number;
  timeout?: number;
  quiet?: boolean;
}

// API request options interface
export interface ApiRequestOptions {
  retryAttempts?: number;
  timeout?: number;
  quiet?: boolean;
}

// Error types for better error handling
export class PiiApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public response?: Response,
    public isRetryable: boolean = false
  ) {
    super(message);
    this.name = 'PiiApiError';
  }
}

export class PiiApiTimeoutError extends PiiApiError {
  constructor(message: string) {
    super(message, undefined, undefined, true);
    this.name = 'PiiApiTimeoutError';
  }
}

export class PiiApiNetworkError extends PiiApiError {
  constructor(message: string) {
    super(message, undefined, undefined, true);
    this.name = 'PiiApiNetworkError';
  }
}

/**
 * Centralized PII API Client
 * 
 * Handles all PII detection API operations with:
 * - Centralized configuration management
 * - Retry logic with exponential backoff
 * - Comprehensive error handling
 * - Request/response logging
 * - Timeout management
 */
export class PiiApiClient {
  private static instance: PiiApiClient | null = null;
  private config: PiiApiClientConfig;
  private abortControllers: Map<string, AbortController> = new Map();

  constructor(config: PiiApiClientConfig) {
    this.config = {
      retryAttempts: 3,
      retryDelay: 1000,
      timeout: 30000,
      quiet: false,
      ...config
    };
  }

  /**
   * Get singleton instance of PiiApiClient
   */
  static getInstance(config?: PiiApiClientConfig): PiiApiClient {
    if (!PiiApiClient.instance || config) {
      if (!config) {
        throw new Error('PiiApiClient must be initialized with config on first use');
      }
      PiiApiClient.instance = new PiiApiClient(config);
    }
    return PiiApiClient.instance;
  }

  /**
   * Update client configuration
   */
  updateConfig(newConfig: Partial<PiiApiClientConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * Get PII API base URL from config or store
   */
  private getBaseUrl(): string {
    if (this.config.baseUrl) {
      return this.config.baseUrl;
    }
    
    const configValue = get(config);
    return (configValue as any)?.pii?.api_base_url || 'https://api.nenna.ai/latest';
  }

  /**
   * Create abort controller for request cancellation
   */
  private createAbortController(requestId: string, timeout: number): AbortController {
    const controller = new AbortController();
    this.abortControllers.set(requestId, controller);
    
    setTimeout(() => {
      if (!controller.signal.aborted) {
        controller.abort();
        this.abortControllers.delete(requestId);
      }
    }, timeout);
    
    return controller;
  }

  /**
   * Sleep function for retry delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Determine if error is retryable
   */
  private isRetryableError(error: any): boolean {
    if (error instanceof PiiApiTimeoutError || error instanceof PiiApiNetworkError) {
      return true;
    }
    
    if (error instanceof PiiApiError) {
      return error.isRetryable;
    }
    
    // Network errors, timeouts, and 5xx errors are retryable
    if (error.name === 'AbortError' || error.name === 'TypeError') {
      return true;
    }
    
    return false;
  }

  /**
   * Make HTTP request with retry logic and error handling
   */
  private async makeRequest<T>(
    url: string,
    options: RequestInit,
    requestOptions: ApiRequestOptions = {}
  ): Promise<T> {
    const requestId = `${Date.now()}-${Math.random()}`;
    const maxAttempts = requestOptions.retryAttempts ?? this.config.retryAttempts!;
    const timeout = requestOptions.timeout ?? this.config.timeout!;
    const quiet = requestOptions.quiet ?? this.config.quiet!;
    
    if (!quiet) {
      console.log(`PiiApiClient: Making request to ${url}`, {
        method: options.method,
        requestId,
        maxAttempts
      });
    }

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const controller = this.createAbortController(requestId, timeout);
        
        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': this.config.apiKey,
            ...options.headers
          }
        });

        this.abortControllers.delete(requestId);

        if (!response.ok) {
          const errorText = await response.text().catch(() => 'Unknown error');
          const isRetryable = response.status >= 500 || response.status === 429;
          
          throw new PiiApiError(
            `API request failed: ${response.status} ${response.statusText} - ${errorText}`,
            response.status,
            response,
            isRetryable
          );
        }

        const data = await response.json();
        
        if (!quiet) {
          console.log(`PiiApiClient: Request successful`, {
            requestId,
            attempt,
            status: response.status
          });
        }
        
        return data;

      } catch (error) {
        this.abortControllers.delete(requestId);
        
        // Handle specific error types
        let handledError = error;
        if ((error as any)?.name === 'AbortError') {
          handledError = new PiiApiTimeoutError(`Request timeout after ${timeout}ms`);
        } else if (error instanceof TypeError && error.message.includes('fetch')) {
          handledError = new PiiApiNetworkError(`Network error: ${error.message}`);
        }
        error = handledError;

        const isLastAttempt = attempt === maxAttempts;
        const shouldRetry = !isLastAttempt && this.isRetryableError(error);

        if (!quiet) {
          console.log(`PiiApiClient: Request failed`, {
            requestId,
            attempt,
            maxAttempts,
            error: (error as any)?.message || String(error),
            shouldRetry
          });
        }

        if (!shouldRetry) {
          throw error;
        }

        // Exponential backoff delay
        const delay = this.config.retryDelay! * Math.pow(2, attempt - 1);
        await this.sleep(delay);
      }
    }

    throw new Error('Max retry attempts reached'); // Should never happen
  }

  /**
   * Create a session for consistent masking/unmasking
   */
  async createSession(
    ttl: string = '24h',
    options: ApiRequestOptions = {}
  ): Promise<PiiSession> {
    const url = `${this.getBaseUrl()}/sessions`;
    
    return this.makeRequest<PiiSession>(url, {
      method: 'POST',
      body: JSON.stringify({
        ttl,
        description: 'Open WebUI PII Detection Session'
      })
    }, options);
  }

  /**
   * Get session information
   */
  async getSession(
    sessionId: string,
    options: ApiRequestOptions = {}
  ): Promise<PiiSession> {
    const url = `${this.getBaseUrl()}/sessions/${sessionId}`;
    
    return this.makeRequest<PiiSession>(url, {
      method: 'GET'
    }, options);
  }

  /**
   * Delete a session
   */
  async deleteSession(
    sessionId: string,
    options: ApiRequestOptions = {}
  ): Promise<void> {
    const url = `${this.getBaseUrl()}/sessions/${sessionId}`;
    
    await this.makeRequest<void>(url, {
      method: 'DELETE'
    }, options);
  }

  /**
   * Mask PII in text (ephemeral - without session)
   */
  async maskText(
    text: string[],
    knownEntities: KnownPiiEntity[] = [],
    modifiers: ShieldApiModifier[] = [],
    createSession: boolean = false,
    options: ApiRequestOptions = {}
  ): Promise<PiiMaskResponse> {
    const url = new URL(`${this.getBaseUrl()}/text/mask`);
    
    if (createSession) {
      url.searchParams.set('create_session', 'true');
    }
    
    if (options.quiet ?? this.config.quiet) {
      url.searchParams.set('quiet', 'true');
    }

    const requestBody: {
      text: string[];
      pii_labels: { detect: string[] };
      known_entities?: KnownPiiEntity[];
      modifiers?: ShieldApiModifier[];
    } = {
      text,
      pii_labels: {
        detect: ['ALL']
      }
    };

    if (knownEntities.length > 0) {
      requestBody.known_entities = knownEntities;
    }

    if (modifiers.length > 0) {
      requestBody.modifiers = modifiers;
    }

    return this.makeRequest<PiiMaskResponse>(url.toString(), {
      method: 'POST',
      body: JSON.stringify(requestBody)
    }, options);
  }

  /**
   * Unmask PII in text (ephemeral - without session)
   */
  async unmaskText(
    text: string[],
    entities: PiiEntity[],
    options: ApiRequestOptions = {}
  ): Promise<PiiUnmaskResponse> {
    const url = `${this.getBaseUrl()}/text/unmask`;
    
    return this.makeRequest<PiiUnmaskResponse>(url, {
      method: 'POST',
      body: JSON.stringify({
        text,
        entities
      })
    }, options);
  }

  /**
   * Mask PII in text using session
   */
  async maskTextWithSession(
    sessionId: string,
    text: string[],
    knownEntities: KnownPiiEntity[] = [],
    modifiers: ShieldApiModifier[] = [],
    options: ApiRequestOptions = {}
  ): Promise<PiiMaskResponse> {
    const url = new URL(`${this.getBaseUrl()}/sessions/${sessionId}/text/mask`);
    
    if (options.quiet ?? this.config.quiet) {
      url.searchParams.set('quiet', 'true');
    }

    const requestBody: {
      text: string[];
      pii_labels: { detect: string[] };
      known_entities?: KnownPiiEntity[];
      modifiers?: ShieldApiModifier[];
    } = {
      text,
      pii_labels: {
        detect: ['ALL']
      }
    };

    if (knownEntities.length > 0) {
      requestBody.known_entities = knownEntities;
    }

    if (modifiers.length > 0) {
      requestBody.modifiers = modifiers;
    }

    return this.makeRequest<PiiMaskResponse>(url.toString(), {
      method: 'POST',
      body: JSON.stringify(requestBody)
    }, options);
  }

  /**
   * Unmask PII in text using session
   */
  async unmaskTextWithSession(
    sessionId: string,
    text: string[],
    options: ApiRequestOptions = {}
  ): Promise<PiiUnmaskResponse> {
    const url = `${this.getBaseUrl()}/sessions/${sessionId}/text/unmask`;
    
    return this.makeRequest<PiiUnmaskResponse>(url, {
      method: 'POST',
      body: JSON.stringify({
        text
      })
    }, options);
  }

  /**
   * Cancel all pending requests
   */
  cancelAllRequests(): void {
    console.log(`PiiApiClient: Cancelling ${this.abortControllers.size} pending requests`);
    
    for (const [requestId, controller] of this.abortControllers) {
      controller.abort();
    }
    
    this.abortControllers.clear();
  }

  /**
   * Cancel specific request by ID
   */
  cancelRequest(requestId: string): boolean {
    const controller = this.abortControllers.get(requestId);
    if (controller) {
      controller.abort();
      this.abortControllers.delete(requestId);
      return true;
    }
    return false;
  }

  /**
   * Get client statistics
   */
  getStats(): {
    pendingRequests: number;
    config: PiiApiClientConfig;
  } {
    return {
      pendingRequests: this.abortControllers.size,
      config: { ...this.config }
    };
  }
}

// Export convenience functions for backward compatibility
export const createPiiApiClient = (config: PiiApiClientConfig): PiiApiClient => {
  return PiiApiClient.getInstance(config);
};

export const getPiiApiClient = (): PiiApiClient => {
  return PiiApiClient.getInstance();
}; 