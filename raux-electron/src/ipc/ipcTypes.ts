export interface StatusMessage {
  type: 'info' | 'progress' | 'error' | 'success';
  message: string;
  progress?: number; // 0-100 for progress updates
  step?: string; // Current installation step
} 