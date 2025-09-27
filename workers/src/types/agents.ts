// Core Agent Interfaces for OrcaAI Real Estate Assistant

export interface Agent {
  id: string;
  name: string;
  version: string;
  initialize(config: AgentConfig): Promise<void>;
  handleMessage(message: string, context: AgentContext): Promise<AgentResponse>;
  cleanup(): Promise<void>;
}

export interface AgentConfig {
  aiModel: string;
  apiKeys: Record<string, string>;
  rateLimits: RateLimitConfig;
  caching: CacheConfig;
}

export interface AgentContext {
  userId: string;
  sessionId: string;
  timestamp: number;
  metadata: Record<string, unknown>;
}

export interface AgentResponse {
  success: boolean;
  content: string;
  actions: AgentAction[];
  error?: string;
  confidence: number;
  requiresCoordination?: boolean;
  alternativeActions?: AgentAction[];
}

export interface AgentAction {
  type: 'email' | 'calendar' | 'crm' | 'document' | 'api_call';
  payload: Record<string, unknown>;
  priority: 'low' | 'medium' | 'high' | 'urgent';
}

export interface RateLimitConfig {
  requestsPerMinute: number;
  requestsPerHour: number;
  requestsPerDay: number;
}

export interface CacheConfig {
  enabled: boolean;
  ttl: number; // Time to live in seconds
  maxSize: number; // Maximum number of cached items
}

export interface AgentError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp: number;
  retryable: boolean;
}

export interface AgentMetrics {
  responseTime: number;
  successRate: number;
  errorCount: number;
  requestCount: number;
  lastUsed: number;
}

// Agent Registry for managing multiple agents
export interface AgentRegistry {
  register(agent: Agent): void;
  get(agentId: string): Agent | undefined;
  getAll(): Agent[];
  unregister(agentId: string): boolean;
}

// Workflow coordination interfaces
export interface WorkflowStep {
  id: string;
  agentId: string;
  action: string;
  payload: Record<string, unknown>;
  dependencies: string[]; // IDs of steps this depends on
  timeout: number; // in milliseconds
  retryCount: number;
  retryDelay: number; // in milliseconds
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  steps: WorkflowStep[];
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
  error?: AgentError;
}

export interface WorkflowContext {
  workflowId: string;
  userId: string;
  sessionId: string;
  data: Record<string, unknown>;
  stepResults: Record<string, unknown>;
}

// Event system for agent communication
export interface AgentEvent {
  id: string;
  type: string;
  source: string; // agent ID
  target?: string; // agent ID (if directed)
  payload: Record<string, unknown>;
  timestamp: number;
}

export interface EventHandler {
  eventType: string;
  handler: (event: AgentEvent) => Promise<void>;
  priority: number;
}

// Configuration for specific agents
export interface GmailAgentConfig extends AgentConfig {
  oauth: {
    clientId: string;
    clientSecret: string;
    redirectUri: string;
    scopes: string[];
  };
  emailFilters: {
    propertyKeywords: string[];
    excludeDomains: string[];
    maxAge: string; // e.g., "7d"
  };
}

export interface CRMAgentConfig extends AgentConfig {
  sheets: {
    spreadsheetId: string;
    sheetsConfig: {
      leads: string;
      properties: string;
      showings: string;
      activities: string;
    };
  };
  pipeline: {
    stages: string[];
    defaultStage: string;
    autoProgress: boolean;
  };
}

export interface CalendarAgentConfig extends AgentConfig {
  calendar: {
    calendarId: string;
    defaultDuration: number; // in minutes
    bufferTime: number; // in minutes between appointments
    workingHours: {
      start: string; // "09:00"
      end: string; // "17:00"
      timezone: string;
    };
  };
  reminders: {
    email: number; // hours before
    sms: number; // hours before
    push: number; // minutes before
  };
}

export interface DriveAgentConfig extends AgentConfig {
  drive: {
    folderStructure: {
      root: string;
      properties: string;
      clients: string;
      templates: string;
    };
    sharing: {
      defaultPermission: 'viewer' | 'commenter' | 'editor';
      expirationDays: number;
    };
  };
  templates: {
    propertyPacket: string;
    coverLetter: string;
    disclosure: string;
  };
}
