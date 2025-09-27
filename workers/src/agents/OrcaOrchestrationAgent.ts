// OrcaOrchestrationAgent - Main orchestrator for real estate AI agents
import type { 
  Agent, 
  AgentConfig, 
  AgentContext, 
  AgentResponse, 
  AgentAction,
  GmailAgentConfig,
  CRMAgentConfig,
  CalendarAgentConfig,
  DriveAgentConfig
} from '../types/agents.js';
import type { RealEstateAction } from '../types/intent.js';

// Import specialized agents (these will be implemented later)
import type { GmailAgent } from './gmail/GmailAgent.js';
import type { CRMSheetsAgent } from './crm/CRMSheetsAgent.js';
import type { CalendarAgent } from './calendar/CalendarAgent.js';
import type { DriveAgent } from './drive/DriveAgent.js';

// Import AI client and storage
import type { GLMClient } from '../ai/GLMClient.js';
import type { DurableObjectStorage } from '../storage/DurableObjectStorage.js';

export interface OrcaConfig {
  ai: GLMClient;
  gmail: GmailAgent;
  crm: CRMSheetsAgent;
  calendar: CalendarAgent;
  drive: DriveAgent;
  storage: DurableObjectStorage;
}

export class OrcaOrchestrationAgent implements Agent {
  public readonly id = 'orca-orchestration';
  public readonly name = 'OrcaAI Real Estate Assistant';
  public readonly version = '1.0.0';

  private gmailAgent: GmailAgent;
  private crmAgent: CRMSheetsAgent;
  private calendarAgent: CalendarAgent;
  private driveAgent: DriveAgent;
  private aiClient: GLMClient;
  private storage: DurableObjectStorage;

  constructor(config: OrcaConfig) {
    this.aiClient = config.ai;
    this.gmailAgent = config.gmail;
    this.crmAgent = config.crm;
    this.calendarAgent = config.calendar;
    this.driveAgent = config.drive;
    this.storage = config.storage;
  }

  async initialize(config?: AgentConfig): Promise<void> {
    // Initialize all agents and AI client in parallel
    await Promise.all([
      this.aiClient.initialize(),
      this.gmailAgent.initialize(config as GmailAgentConfig),
      this.crmAgent.initialize(config as CRMAgentConfig),
      this.calendarAgent.initialize(config as CalendarAgentConfig),
      this.driveAgent.initialize(config as DriveAgentConfig)
    ]);
  }

  async handleMessage(message: string, context: AgentContext): Promise<AgentResponse> {
    try {
      // 1. Analyze user intent using AI
      const intent = await this.aiClient.analyzeIntent(message);
      
      // 2. Route to appropriate specialized agent
      const agent = this.routeToAgent(intent.primaryAction);
      
      // 3. Execute agent workflow
      const response = await agent.handleMessage(intent, context);
      
      // 4. Store conversation history for continuity
      await this.storage.storeConversation({
        userId: context.userId,
        message,
        intent,
        response,
        timestamp: Date.now()
      });
      
      // 5. Check if multi-agent coordination is needed
      if (response.requiresCoordination && response.actions.length > 0) {
        return await this.coordinateWorkflow(response, context);
      }
      
      return response;
    } catch (error) {
      return this.handleError(error, context);
    }
  }

  private routeToAgent(action: RealEstateAction): Agent {
    switch (action) {
      // Email-related actions
      case 'email_check':
      case 'email_response':
        return this.gmailAgent;
      
      // Calendar and scheduling actions
      case 'schedule_showing':
      case 'reschedule_showing':
      case 'cancel_showing':
      case 'calendar_management':
        return this.calendarAgent;
      
      // CRM and lead management actions
      case 'crm_update':
      case 'lead_management':
      case 'lead_qualification':
        return this.crmAgent;
      
      // Document and property packet actions
      case 'document_request':
      case 'property_packet':
        return this.driveAgent;
      
      // Market analysis and complex actions that may require coordination
      case 'market_analysis':
      case 'price_analysis':
      case 'neighborhood_info':
      case 'mortgage_calculation':
      case 'investment_analysis':
      case 'rental_analysis':
      case 'comparable_properties':
      case 'property_valuation':
        // These may require multiple agents - start with CRM as primary
        return this.crmAgent;
      
      // Showing and feedback actions
      case 'showing_feedback':
        return this.calendarAgent;
      
      // Transaction-related actions
      case 'offer_preparation':
      case 'negotiation_assistance':
      case 'closing_coordination':
      case 'post_closing_followup':
        // These typically involve CRM coordination
        return this.crmAgent;
      
      // Follow-up sequences
      case 'follow_up_sequence':
        return this.gmailAgent;
      
      default:
        throw new Error(`Unsupported action: ${action}`);
    }
  }

  private async coordinateWorkflow(response: AgentResponse, context: AgentContext): Promise<AgentResponse> {
    const coordinatedActions: AgentAction[] = [];
    const additionalResponses: AgentResponse[] = [];
    
    // Process each action that may require coordination
    for (const action of response.actions) {
      switch (action.type) {
        case 'email':
          // If CRM action is needed alongside email
          if (action.payload.leadId) {
            const crmAction: AgentAction = {
              type: 'crm',
              payload: {
                action: 'log_email_activity',
                leadId: action.payload.leadId,
                emailContent: response.content
              },
              priority: action.priority
            };
            coordinatedActions.push(crmAction);
          }
          break;
          
        case 'calendar':
          // If showing is scheduled, update CRM and send email
          if (action.payload.showingId) {
            const crmAction: AgentAction = {
              type: 'crm',
              payload: {
                action: 'update_showing_status',
                showingId: action.payload.showingId,
                status: 'scheduled'
              },
              priority: action.priority
            };
            coordinatedActions.push(crmAction);
            
            const emailAction: AgentAction = {
              type: 'email',
              payload: {
                action: 'send_showing_confirmation',
                showingId: action.payload.showingId
              },
              priority: action.priority
            };
            coordinatedActions.push(emailAction);
          }
          break;
          
        case 'document':
          // If property packet is created, log in CRM and send notification
          if (action.payload.packetId) {
            const crmAction: AgentAction = {
              type: 'crm',
              payload: {
                action: 'log_document_packet',
                packetId: action.payload.packetId
              },
              priority: action.priority
            };
            coordinatedActions.push(crmAction);
          }
          break;
      }
    }
    
    // Execute coordinated actions
    for (const action of coordinatedActions) {
      const agent = this.routeToAgent(this.getActionTypeFromPayload(action));
      try {
        const agentResponse = await agent.handleMessage(
          `Execute coordinated action: ${action.type}`,
          context
        );
        additionalResponses.push(agentResponse);
      } catch (error) {
        // Log coordination errors but don't fail the entire workflow
        console.error('Coordination error:', error);
      }
    }
    
    // Return enhanced response with coordination results
    return {
      ...response,
      actions: [...response.actions, ...coordinatedActions],
      content: this.enhanceResponseWithCoordination(response.content, additionalResponses)
    };
  }

  private getActionTypeFromPayload(action: AgentAction): RealEstateAction {
    switch (action.type) {
      case 'email':
        return 'email_response';
      case 'calendar':
        return 'calendar_management';
      case 'crm':
        return 'crm_update';
      case 'document':
        return 'document_request';
      default:
        return 'crm_update'; // fallback
    }
  }

  private enhanceResponseWithCoordination(baseContent: string, additionalResponses: AgentResponse[]): string {
    if (additionalResponses.length === 0) {
      return baseContent;
    }
    
    const coordinationSummary = additionalResponses
      .filter(r => r.success)
      .map(r => r.content)
      .join(' ');
    
    return `${baseContent}\n\nAdditionally: ${coordinationSummary}`;
  }

  private handleError(error: unknown, context: AgentContext): AgentResponse {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    // Log error for debugging
    console.error('OrcaOrchestrationAgent error:', {
      error: errorMessage,
      userId: context.userId,
      timestamp: new Date().toISOString()
    });
    
    // Determine if error is retryable and suggest alternative actions
    this.isErrorRetryable(error);
    const alternativeActions = this.generateAlternativeActions(error);
    
    return {
      success: false,
      content: `I encountered an error while processing your request: ${errorMessage}`,
      actions: [],
      error: errorMessage,
      confidence: 0,
      requiresCoordination: false,
      alternativeActions
    };
  }

  private isErrorRetryable(error: unknown): boolean {
    if (error instanceof Error) {
      // Network-related errors are typically retryable
      const retryableErrors = [
        'ECONNRESET',
        'ETIMEDOUT',
        'ENOTFOUND',
        'EAI_AGAIN',
        'Network Error',
        'Timeout',
        'Rate Limit'
      ];
      
      return retryableErrors.some(retryableError => 
        error.message.includes(retryableError)
      );
    }
    return false;
  }

  private generateAlternativeActions(error: unknown): AgentAction[] {
    const actions: AgentAction[] = [];
    
    if (error instanceof Error) {
      if (error.message.includes('Gmail') || error.message.includes('email')) {
        actions.push({
          type: 'crm',
          payload: { action: 'check_email_status' },
          priority: 'medium'
        });
      }
      
      if (error.message.includes('Calendar') || error.message.includes('showing')) {
        actions.push({
          type: 'crm',
          payload: { action: 'manually_schedule_showing' },
          priority: 'high'
        });
      }
      
      if (error.message.includes('CRM') || error.message.includes('lead')) {
        actions.push({
          type: 'email',
          payload: { action: 'notify_lead_of_issue' },
          priority: 'medium'
        });
      }
    }
    
    // Always provide a general fallback action
    actions.push({
      type: 'crm',
      payload: { action: 'log_error_for_review' },
      priority: 'low'
    });
    
    return actions;
  }

  async cleanup(): Promise<void> {
    // Cleanup all agents and resources in parallel
    await Promise.all([
      this.aiClient.cleanup(),
      this.gmailAgent.cleanup(),
      this.crmAgent.cleanup(),
      this.calendarAgent.cleanup(),
      this.driveAgent.cleanup(),
      this.storage.cleanup()
    ]);
  }

  // Helper methods for agent health checks and metrics
  async getAgentHealth(): Promise<Record<string, { healthy: boolean; lastUsed: number }>> {
    return {
      gmail: { healthy: true, lastUsed: Date.now() },
      crm: { healthy: true, lastUsed: Date.now() },
      calendar: { healthy: true, lastUsed: Date.now() },
      drive: { healthy: true, lastUsed: Date.now() },
      ai: { healthy: true, lastUsed: Date.now() }
    };
  }

  async getSystemMetrics(): Promise<{
    totalRequests: number;
    successRate: number;
    averageResponseTime: number;
    agentUtilization: Record<string, number>;
  }> {
    // This would be implemented with actual metrics collection
    return {
      totalRequests: 0,
      successRate: 1.0,
      averageResponseTime: 0,
      agentUtilization: {
        gmail: 0,
        crm: 0,
        calendar: 0,
        drive: 0,
        ai: 0
      }
    };
  }
}
