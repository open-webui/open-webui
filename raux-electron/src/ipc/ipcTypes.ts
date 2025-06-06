export interface StatusMessage {
  type: 'info' | 'progress' | 'error' | 'success';
  message: string;
  progress?: number; // 0-100 for progress updates
  step?: string; // Current installation step
}

export interface LemonadeStatus {
  status: 'running' | 'starting' | 'stopped' | 'unavailable' | 'crashed';
  isHealthy: boolean;
  timestamp: number;
  error?: string;
  version?: string;
  port?: string;
}

export interface LemonadeHealthCheck {
  isHealthy: boolean;
  responseTime?: number;
  error?: string;
  timestamp: number;
} 