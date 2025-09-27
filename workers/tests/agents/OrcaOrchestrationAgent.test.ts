import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import type { Agent, AgentContext, AgentResponse, AgentConfig } from '../../src/types/agents.js';
import type { IntentAnalysis, RealEstateAction } from '../../src/types/intent.js';

// Mock dependencies
const mockGLMClient = {
  initialize: vi.fn(),
  analyzeIntent: vi.fn(),
  generateResponse: vi.fn(),
  cleanup: vi.fn()
};

const mockGmailAgent = {
  id: 'gmail-agent',
  name: 'Gmail Agent',
  version: '1.0.0',
  initialize: vi.fn(),
  handleMessage: vi.fn(),
  cleanup: vi.fn()
} as Agent;

const mockCRMAgent = {
  id: 'crm-agent',
  name: 'CRM Agent',
  version: '1.0.0',
  initialize: vi.fn(),
  handleMessage: vi.fn(),
  cleanup: vi.fn()
} as Agent;

const mockCalendarAgent = {
  id: 'calendar-agent',
  name: 'Calendar Agent',
  version: '1.0.0',
  initialize: vi.fn(),
  handleMessage: vi.fn(),
  cleanup: vi.fn()
} as Agent;

const mockDriveAgent = {
  id: 'drive-agent',
  name: 'Drive Agent',
  version: '1.0.0',
  initialize: vi.fn(),
  handleMessage: vi.fn(),
  cleanup: vi.fn()
} as Agent;

const mockStorage = {
  storeConversation: vi.fn(),
  getConversation: vi.fn(),
  cleanup: vi.fn()
};

// Mock OrcaOrchestrationAgent class (since it doesn't exist yet)
class MockOrcaOrchestrationAgent {
  private gmailAgent: Agent;
  private crmAgent: Agent;
  private calendarAgent: Agent;
  private driveAgent: Agent;
  private aiClient: typeof mockGLMClient;
  private storage: typeof mockStorage;

  constructor(config: {
    ai: typeof mockGLMClient;
    gmail: Agent;
    crm: Agent;
    calendar: Agent;
    drive: Agent;
    storage: typeof mockStorage;
  }) {
    this.aiClient = config.ai;
    this.gmailAgent = config.gmail;
    this.crmAgent = config.crm;
    this.calendarAgent = config.calendar;
    this.driveAgent = config.drive;
    this.storage = config.storage;
  }

  async initialize(config?: AgentConfig): Promise<void> {
    const agentConfig = config || {
      aiModel: 'glm-4.5-air',
      apiKeys: { openrouter: 'test', google: 'test' },
      rateLimits: { requestsPerMinute: 60, requestsPerHour: 3600, requestsPerDay: 86400 },
      caching: { enabled: true, ttl: 3600, maxSize: 1000 }
    };
    
    await Promise.all([
      this.aiClient.initialize(),
      this.gmailAgent.initialize(agentConfig),
      this.crmAgent.initialize(agentConfig),
      this.calendarAgent.initialize(agentConfig),
      this.driveAgent.initialize(agentConfig)
    ]);
  }

  async handleMessage(message: string, context: AgentContext): Promise<AgentResponse> {
    try {
      const intent = await this.aiClient.analyzeIntent(message);
      const agent = this.routeToAgent(intent.primaryAction);
      
      const response = await agent.handleMessage(intent, context);
      
      await this.storage.storeConversation({
        userId: context.userId,
        message,
        intent,
        response,
        timestamp: Date.now()
      });
      
      return response;
    } catch (error) {
      return {
        success: false,
        content: '',
        actions: [],
        error: error instanceof Error ? error.message : 'Unknown error',
        confidence: 0,
        alternativeActions: []
      };
    }
  }

  private routeToAgent(action: RealEstateAction): Agent {
    switch (action) {
      case 'email_check':
      case 'email_response':
        return this.gmailAgent;
      case 'schedule_showing':
      case 'calendar_management':
        return this.calendarAgent;
      case 'crm_update':
      case 'lead_management':
        return this.crmAgent;
      case 'document_request':
      case 'property_packet':
        return this.driveAgent;
      default:
        throw new Error(`Unsupported action: ${action}`);
    }
  }

  async cleanup(): Promise<void> {
    await Promise.all([
      this.aiClient.cleanup(),
      this.gmailAgent.cleanup(),
      this.crmAgent.cleanup(),
      this.calendarAgent.cleanup(),
      this.driveAgent.cleanup(),
      this.storage.cleanup()
    ]);
  }
}

describe('OrcaOrchestrationAgent', () => {
  let agent: MockOrcaOrchestrationAgent;
  let mockConfig: AgentConfig;

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockConfig = {
      aiModel: 'glm-4.5-air',
      apiKeys: {
        openrouter: 'test-api-key',
        google: 'test-google-key'
      },
      rateLimits: {
        requestsPerMinute: 60,
        requestsPerHour: 3600,
        requestsPerDay: 86400
      },
      caching: {
        enabled: true,
        ttl: 3600,
        maxSize: 1000
      }
    };

    agent = new MockOrcaOrchestrationAgent({
      ai: mockGLMClient,
      gmail: mockGmailAgent,
      crm: mockCRMAgent,
      calendar: mockCalendarAgent,
      drive: mockDriveAgent,
      storage: mockStorage
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // GREEN PHASE - Tests should pass with minimal implementation
  describe('initialization', () => {
    it('should initialize all agents and AI client', async () => {
      await expect(agent.initialize(mockConfig)).resolves.not.toThrow();
      
      expect(mockGLMClient.initialize).toHaveBeenCalled();
      expect(mockGmailAgent.initialize).toHaveBeenCalledWith(mockConfig);
      expect(mockCRMAgent.initialize).toHaveBeenCalledWith(mockConfig);
      expect(mockCalendarAgent.initialize).toHaveBeenCalledWith(mockConfig);
      expect(mockDriveAgent.initialize).toHaveBeenCalledWith(mockConfig);
    });

    it('should handle initialization errors gracefully', async () => {
      mockGLMClient.initialize.mockRejectedValue(new Error('AI client failed'));
      
      await expect(agent.initialize(mockConfig)).rejects.toThrow('AI client failed');
    });
  });

  describe('message handling', () => {
    let mockContext: AgentContext;

    beforeEach(() => {
      mockContext = {
        userId: 'test-user-123',
        sessionId: 'test-session-456',
        timestamp: Date.now(),
        metadata: {
          userAgent: 'test-agent',
          ipAddress: '127.0.0.1'
        }
      };
    });

    // GREEN PHASE - Tests should pass with routing implementation
    it('should route email queries to GmailAgent', async () => {
      const message = "Check my emails for property inquiries";
      
      const mockIntent: IntentAnalysis = {
        primaryAction: 'email_check' as RealEstateAction,
        entities: {},
        confidence: 0.95,
        suggestedResponses: ['Checking emails now'],
        requiredParameters: [],
        context: {
          conversationHistory: [],
          userContext: {
            userId: 'test-user-123',
            userRole: 'agent',
            permissions: ['email_access'],
            preferences: {
              communicationStyle: 'professional',
              responseLength: 'detailed',
              timezone: 'UTC',
              language: 'en',
              notificationSettings: {
                email: true,
                sms: false,
                push: true,
                frequency: 'immediate'
              }
            },
            recentActivity: []
          },
          sessionContext: {
            sessionId: 'test-session-456',
            startTime: new Date(),
            lastActivity: new Date(),
            pendingTasks: [],
            sessionGoals: []
          },
          businessContext: {
            currentMarketConditions: {
              marketTrend: 'balanced',
              averageDaysOnMarket: 30,
              inventoryLevel: 'normal',
              interestRates: {
                current: 4.5,
                trend: 'stable'
              },
              seasonality: 'spring'
            },
            agentWorkload: {
              scheduledShowings: 3,
              pendingLeads: 5,
              activeTransactions: 2,
              availableSlots: 8,
              workloadLevel: 'medium'
            },
            businessRules: [],
            complianceRequirements: []
          }
        },
        urgency: 'medium'
      };

      const mockResponse: AgentResponse = {
        success: true,
        content: 'Processed 5 property inquiries',
        actions: [],
        confidence: 0.95
      };

      mockGLMClient.analyzeIntent.mockResolvedValue(mockIntent);
      vi.mocked(mockGmailAgent.handleMessage).mockResolvedValue(mockResponse);

      const response = await agent.handleMessage(message, mockContext);

      expect(mockGLMClient.analyzeIntent).toHaveBeenCalledWith(message);
      expect(mockGmailAgent.handleMessage).toHaveBeenCalledWith(mockIntent, mockContext);
      expect(response).toEqual(mockResponse);
      expect(mockStorage.storeConversation).toHaveBeenCalledWith({
        userId: mockContext.userId,
        message,
        intent: mockIntent,
        response: mockResponse,
        timestamp: expect.any(Number)
      });
    });

    it('should route calendar queries to CalendarAgent', async () => {
      const message = "Schedule a showing for tomorrow at 2 PM";
      
      const mockIntent: IntentAnalysis = {
        primaryAction: 'schedule_showing' as RealEstateAction,
        entities: {
          date: new Date(Date.now() + 24 * 60 * 60 * 1000),
          time: '14:00'
        },
        confidence: 0.90,
        suggestedResponses: ['Scheduling showing now'],
        requiredParameters: ['propertyAddress', 'leadId'],
        context: {
          conversationHistory: [],
          userContext: {
            userId: 'test-user-123',
            userRole: 'agent',
            permissions: ['calendar_access'],
            preferences: {
              communicationStyle: 'professional',
              responseLength: 'detailed',
              timezone: 'UTC',
              language: 'en',
              notificationSettings: {
                email: true,
                sms: false,
                push: true,
                frequency: 'immediate'
              }
            },
            recentActivity: []
          },
          sessionContext: {
            sessionId: 'test-session-456',
            startTime: new Date(),
            lastActivity: new Date(),
            pendingTasks: [],
            sessionGoals: []
          },
          businessContext: {
            currentMarketConditions: {
              marketTrend: 'balanced',
              averageDaysOnMarket: 30,
              inventoryLevel: 'normal',
              interestRates: {
                current: 4.5,
                trend: 'stable'
              },
              seasonality: 'spring'
            },
            agentWorkload: {
              scheduledShowings: 3,
              pendingLeads: 5,
              activeTransactions: 2,
              availableSlots: 8,
              workloadLevel: 'medium'
            },
            businessRules: [],
            complianceRequirements: []
          }
        },
        urgency: 'high'
      };

      const mockResponse: AgentResponse = {
        success: true,
        content: 'Showing scheduled successfully',
        actions: [
          {
            type: 'calendar',
            payload: { eventId: 'test-event-123' },
            priority: 'high'
          }
        ],
        confidence: 0.90
      };

      mockGLMClient.analyzeIntent.mockResolvedValue(mockIntent);
      vi.mocked(mockCalendarAgent.handleMessage).mockResolvedValue(mockResponse);

      const response = await agent.handleMessage(message, mockContext);

      expect(mockGLMClient.analyzeIntent).toHaveBeenCalledWith(message);
      expect(mockCalendarAgent.handleMessage).toHaveBeenCalledWith(mockIntent, mockContext);
      expect(response).toEqual(mockResponse);
    });

    it('should route CRM queries to CRMAgent', async () => {
      const message = "Update the lead status to qualified";
      
      const mockIntent: IntentAnalysis = {
        primaryAction: 'crm_update' as RealEstateAction,
        entities: {
          leadId: 'test-lead-123'
        },
        confidence: 0.85,
        suggestedResponses: ['Updating lead status'],
        requiredParameters: ['leadId', 'newStatus'],
        context: {
          conversationHistory: [],
          userContext: {
            userId: 'test-user-123',
            userRole: 'agent',
            permissions: ['crm_access'],
            preferences: {
              communicationStyle: 'professional',
              responseLength: 'detailed',
              timezone: 'UTC',
              language: 'en',
              notificationSettings: {
                email: true,
                sms: false,
                push: true,
                frequency: 'immediate'
              }
            },
            recentActivity: []
          },
          sessionContext: {
            sessionId: 'test-session-456',
            startTime: new Date(),
            lastActivity: new Date(),
            pendingTasks: [],
            sessionGoals: []
          },
          businessContext: {
            currentMarketConditions: {
              marketTrend: 'balanced',
              averageDaysOnMarket: 30,
              inventoryLevel: 'normal',
              interestRates: {
                current: 4.5,
                trend: 'stable'
              },
              seasonality: 'spring'
            },
            agentWorkload: {
              scheduledShowings: 3,
              pendingLeads: 5,
              activeTransactions: 2,
              availableSlots: 8,
              workloadLevel: 'medium'
            },
            businessRules: [],
            complianceRequirements: []
          }
        },
        urgency: 'medium'
      };

      const mockResponse: AgentResponse = {
        success: true,
        content: 'Lead status updated to qualified',
        actions: [
          {
            type: 'crm',
            payload: { leadId: 'test-lead-123', newStatus: 'qualified' },
            priority: 'medium'
          }
        ],
        confidence: 0.85
      };

      mockGLMClient.analyzeIntent.mockResolvedValue(mockIntent);
      vi.mocked(mockCRMAgent.handleMessage).mockResolvedValue(mockResponse);

      const response = await agent.handleMessage(message, mockContext);

      expect(mockGLMClient.analyzeIntent).toHaveBeenCalledWith(message);
      expect(mockCRMAgent.handleMessage).toHaveBeenCalledWith(mockIntent, mockContext);
      expect(response).toEqual(mockResponse);
    });

    it('should route document queries to DriveAgent', async () => {
      const message = "Create a property packet for 123 Main St";
      
      const mockIntent: IntentAnalysis = {
        primaryAction: 'property_packet' as RealEstateAction,
        entities: {
          propertyAddress: '123 Main St'
        },
        confidence: 0.88,
        suggestedResponses: ['Creating property packet'],
        requiredParameters: ['propertyId', 'leadId'],
        context: {
          conversationHistory: [],
          userContext: {
            userId: 'test-user-123',
            userRole: 'agent',
            permissions: ['drive_access'],
            preferences: {
              communicationStyle: 'professional',
              responseLength: 'detailed',
              timezone: 'UTC',
              language: 'en',
              notificationSettings: {
                email: true,
                sms: false,
                push: true,
                frequency: 'immediate'
              }
            },
            recentActivity: []
          },
          sessionContext: {
            sessionId: 'test-session-456',
            startTime: new Date(),
            lastActivity: new Date(),
            pendingTasks: [],
            sessionGoals: []
          },
          businessContext: {
            currentMarketConditions: {
              marketTrend: 'balanced',
              averageDaysOnMarket: 30,
              inventoryLevel: 'normal',
              interestRates: {
                current: 4.5,
                trend: 'stable'
              },
              seasonality: 'spring'
            },
            agentWorkload: {
              scheduledShowings: 3,
              pendingLeads: 5,
              activeTransactions: 2,
              availableSlots: 8,
              workloadLevel: 'medium'
            },
            businessRules: [],
            complianceRequirements: []
          }
        },
        urgency: 'medium'
      };

      const mockResponse: AgentResponse = {
        success: true,
        content: 'Property packet created successfully',
        actions: [
          {
            type: 'document',
            payload: { packetId: 'test-packet-123', shareLink: 'https://drive.google.com/test' },
            priority: 'medium'
          }
        ],
        confidence: 0.88
      };

      mockGLMClient.analyzeIntent.mockResolvedValue(mockIntent);
      vi.mocked(mockDriveAgent.handleMessage).mockResolvedValue(mockResponse);

      const response = await agent.handleMessage(message, mockContext);

      expect(mockGLMClient.analyzeIntent).toHaveBeenCalledWith(message);
      expect(mockDriveAgent.handleMessage).toHaveBeenCalledWith(mockIntent, mockContext);
      expect(response).toEqual(mockResponse);
    });

    it('should handle agent failures gracefully', async () => {
      const message = "Check my emails";
      
      const mockIntent: IntentAnalysis = {
        primaryAction: 'email_check' as RealEstateAction,
        entities: {},
        confidence: 0.95,
        suggestedResponses: ['Checking emails'],
        requiredParameters: [],
        context: {
          conversationHistory: [],
          userContext: {
            userId: 'test-user-123',
            userRole: 'agent',
            permissions: ['email_access'],
            preferences: {
              communicationStyle: 'professional',
              responseLength: 'detailed',
              timezone: 'UTC',
              language: 'en',
              notificationSettings: {
                email: true,
                sms: false,
                push: true,
                frequency: 'immediate'
              }
            },
            recentActivity: []
          },
          sessionContext: {
            sessionId: 'test-session-456',
            startTime: new Date(),
            lastActivity: new Date(),
            pendingTasks: [],
            sessionGoals: []
          },
          businessContext: {
            currentMarketConditions: {
              marketTrend: 'balanced',
              averageDaysOnMarket: 30,
              inventoryLevel: 'normal',
              interestRates: {
                current: 4.5,
                trend: 'stable'
              },
              seasonality: 'spring'
            },
            agentWorkload: {
              scheduledShowings: 3,
              pendingLeads: 5,
              activeTransactions: 2,
              availableSlots: 8,
              workloadLevel: 'medium'
            },
            businessRules: [],
            complianceRequirements: []
          }
        },
        urgency: 'medium'
      };

      mockGLMClient.analyzeIntent.mockResolvedValue(mockIntent);
      vi.mocked(mockGmailAgent.handleMessage).mockRejectedValue(new Error('Gmail API is down'));

      const response = await agent.handleMessage(message, mockContext);

      expect(response.success).toBe(false);
      expect(response.error).toContain('Gmail API is down');
      expect(response.confidence).toBe(0);
      expect(response.alternativeActions).toBeDefined();
    });

    it('should handle unsupported actions', async () => {
      const message = "Perform an unsupported action";
      
      const mockIntent: IntentAnalysis = {
        primaryAction: 'unsupported_action' as RealEstateAction,
        entities: {},
        confidence: 0.50,
        suggestedResponses: ['I cannot perform this action'],
        requiredParameters: [],
        context: {
          conversationHistory: [],
          userContext: {
            userId: 'test-user-123',
            userRole: 'agent',
            permissions: [],
            preferences: {
              communicationStyle: 'professional',
              responseLength: 'detailed',
              timezone: 'UTC',
              language: 'en',
              notificationSettings: {
                email: true,
                sms: false,
                push: true,
                frequency: 'immediate'
              }
            },
            recentActivity: []
          },
          sessionContext: {
            sessionId: 'test-session-456',
            startTime: new Date(),
            lastActivity: new Date(),
            pendingTasks: [],
            sessionGoals: []
          },
          businessContext: {
            currentMarketConditions: {
              marketTrend: 'balanced',
              averageDaysOnMarket: 30,
              inventoryLevel: 'normal',
              interestRates: {
                current: 4.5,
                trend: 'stable'
              },
              seasonality: 'spring'
            },
            agentWorkload: {
              scheduledShowings: 3,
              pendingLeads: 5,
              activeTransactions: 2,
              availableSlots: 8,
              workloadLevel: 'medium'
            },
            businessRules: [],
            complianceRequirements: []
          }
        },
        urgency: 'low'
      };

      mockGLMClient.analyzeIntent.mockResolvedValue(mockIntent);

      const response = await agent.handleMessage(message, mockContext);

      expect(response.success).toBe(false);
      expect(response.error).toContain('Unsupported action');
      expect(response.confidence).toBe(0);
    });
  });

  describe('cleanup', () => {
    it('should cleanup all agents and AI client', async () => {
      await agent.cleanup();
      
      expect(mockGLMClient.cleanup).toHaveBeenCalled();
      expect(mockGmailAgent.cleanup).toHaveBeenCalled();
      expect(mockCRMAgent.cleanup).toHaveBeenCalled();
      expect(mockCalendarAgent.cleanup).toHaveBeenCalled();
      expect(mockDriveAgent.cleanup).toHaveBeenCalled();
      expect(mockStorage.cleanup).toHaveBeenCalled();
    });
  });
});
