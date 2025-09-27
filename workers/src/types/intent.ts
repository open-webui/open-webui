// AI Intent Analysis Types for OrcaAI Real Estate Assistant
import type { PropertyPreferences } from './real-estate.js';
import type { AgentAction } from './agents.js';

export interface IntentAnalysis {
  primaryAction: RealEstateAction;
  entities: IntentEntities;
  confidence: number;
  suggestedResponses: string[];
  requiredParameters: string[];
  context: IntentContext;
  urgency: 'low' | 'medium' | 'high' | 'urgent';
}

export type RealEstateAction = 
  | 'email_check'
  | 'email_response'
  | 'schedule_showing'
  | 'reschedule_showing'
  | 'cancel_showing'
  | 'calendar_management'
  | 'crm_update'
  | 'lead_management'
  | 'document_request'
  | 'property_search'
  | 'property_packet'
  | 'lead_qualification'
  | 'follow_up_sequence'
  | 'market_analysis'
  | 'price_analysis'
  | 'neighborhood_info'
  | 'mortgage_calculation'
  | 'investment_analysis'
  | 'rental_analysis'
  | 'comparable_properties'
  | 'property_valuation'
  | 'showing_feedback'
  | 'offer_preparation'
  | 'negotiation_assistance'
  | 'closing_coordination'
  | 'post_closing_followup';

export interface IntentEntities {
  // Person entities
  buyerName?: string;
  sellerName?: string;
  agentName?: string;
  contactName?: string;
  
  // Property entities
  propertyAddress?: string;
  propertyId?: string;
  mlsNumber?: string;
  propertyName?: string;
  
  // Temporal entities
  date?: Date;
  time?: string;
  timeframe?: string;
  deadline?: Date;
  
  // Financial entities
  budget?: number;
  price?: number;
  offerAmount?: number;
  downPayment?: number;
  mortgageAmount?: number;
  
  // Property preferences
  propertyType?: string;
  bedrooms?: number;
  bathrooms?: number;
  squareFeet?: number;
  location?: string;
  neighborhood?: string;
  city?: string;
  state?: string;
  zipCode?: string;
  
  // Action-specific entities
  showingId?: string;
  leadId?: string;
  documentType?: string;
  emailSubject?: string;
  calendarEventId?: string;
  
  // Contact information
  email?: string;
  phone?: string;
  
  // Additional context
  urgency?: 'low' | 'medium' | 'high' | 'urgent';
  preferences?: PropertyPreferences;
  specialRequests?: string[];
  constraints?: string[];
}

export interface IntentContext {
  conversationHistory: ConversationEntry[];
  userContext: UserContext;
  sessionContext: SessionContext;
  businessContext: BusinessContext;
}

export interface ConversationEntry {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  intent?: IntentAnalysis;
  action?: AgentAction;
}

export interface UserContext {
  userId: string;
  userRole: 'agent' | 'admin' | 'client' | 'lead';
  permissions: string[];
  preferences: UserPreferences;
  recentActivity: RecentActivity[];
}

export interface UserPreferences {
  communicationStyle: 'formal' | 'casual' | 'friendly' | 'professional';
  responseLength: 'concise' | 'detailed' | 'comprehensive';
  timezone: string;
  language: string;
  notificationSettings: NotificationSettings;
}

export interface NotificationSettings {
  email: boolean;
  sms: boolean;
  push: boolean;
  frequency: 'immediate' | 'daily' | 'weekly';
}

export interface RecentActivity {
  type: string;
  description: string;
  timestamp: Date;
  relevanceScore: number;
}

export interface SessionContext {
  sessionId: string;
  startTime: Date;
  lastActivity: Date;
  currentWorkflow?: string;
  pendingTasks: PendingTask[];
  sessionGoals: string[];
}

export interface PendingTask {
  id: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  dueDate?: Date;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
}

export interface BusinessContext {
  currentMarketConditions: MarketConditions;
  agentWorkload: AgentWorkload;
  businessRules: BusinessRule[];
  complianceRequirements: ComplianceRequirement[];
}

export interface MarketConditions {
  marketTrend: 'buyer' | 'seller' | 'balanced';
  averageDaysOnMarket: number;
  inventoryLevel: 'low' | 'normal' | 'high';
  interestRates: {
    current: number;
    trend: 'rising' | 'falling' | 'stable';
  };
  seasonality: 'spring' | 'summer' | 'fall' | 'winter';
}

export interface AgentWorkload {
  scheduledShowings: number;
  pendingLeads: number;
  activeTransactions: number;
  availableSlots: number;
  workloadLevel: 'low' | 'medium' | 'high' | 'overloaded';
}

export interface BusinessRule {
  id: string;
  name: string;
  description: string;
  condition: string;
  action: string;
  priority: number;
  isActive: boolean;
}

export interface ComplianceRequirement {
  id: string;
  regulation: string;
  description: string;
  requiredActions: string[];
  monitoringNeeded: boolean;
}

// Intent Classification Results
export interface IntentClassification {
  intent: IntentAnalysis;
  alternatives: IntentAnalysis[];
  confidence: number;
  reasoning: string;
  modelUsed: string;
  processingTime: number;
}

// Intent Validation
export interface IntentValidation {
  isValid: boolean;
  confidence: number;
  missingParameters: string[];
  conflictingParameters: string[];
  suggestions: string[];
  riskLevel: 'low' | 'medium' | 'high';
}

// Intent Processing Pipeline
export interface IntentProcessingResult {
  originalQuery: string;
  classifiedIntent: IntentAnalysis;
  validation: IntentValidation;
  selectedAction: RealEstateAction;
  agentRouting: AgentRouting;
  responsePlan: ResponsePlan;
  estimatedProcessingTime: number;
}

export interface AgentRouting {
  primaryAgent: string;
  secondaryAgents?: string[];
  coordinationRequired: boolean;
  executionOrder: string[];
}

export interface ResponsePlan {
  immediateResponse: string;
  followUpActions: FollowUpAction[];
  expectedOutcomes: string[];
  successCriteria: string[];
}

export interface FollowUpAction {
  type: 'email' | 'sms' | 'call' | 'task' | 'notification';
  recipient: string;
  content: string;
  timing: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
}

// Intent Learning and Improvement
export interface IntentFeedback {
  intentId: string;
  originalQuery: string;
  classifiedIntent: IntentAnalysis;
  userCorrection?: IntentAnalysis;
  satisfaction: number; // 1-5
  feedback: string;
  timestamp: Date;
}

export interface IntentModelMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  confusionMatrix: ConfusionMatrix;
  improvementSuggestions: string[];
}

export interface ConfusionMatrix {
  matrix: number[][];
  labels: string[];
}

// Intent Templates for Common Scenarios
export interface IntentTemplate {
  id: string;
  name: string;
  description: string;
  action: RealEstateAction;
  requiredEntities: string[];
  optionalEntities: string[];
  exampleQueries: string[];
  responseTemplate: string;
  confidenceThreshold: number;
}

// Intent Context Enhancement
export interface ContextEnhancer {
  enrichIntent(intent: IntentAnalysis, context: IntentContext): Promise<IntentAnalysis>;
  extractAdditionalEntities(query: string, context: IntentContext): Promise<IntentEntities>;
  validateIntentCompleteness(intent: IntentAnalysis): IntentValidation;
}

// Intent Performance Monitoring
export interface IntentPerformanceMetrics {
  totalQueries: number;
  successfulClassifications: number;
  averageConfidence: number;
  averageProcessingTime: number;
  topActions: ActionMetric[];
  errorRate: number;
  userSatisfaction: number;
}

export interface ActionMetric {
  action: RealEstateAction;
  count: number;
  percentage: number;
  averageConfidence: number;
  successRate: number;
}

// Intent Security and Privacy
export interface IntentSecurity {
  dataPrivacyCheck(intent: IntentAnalysis): boolean;
  permissionValidation(intent: IntentAnalysis, userContext: UserContext): boolean;
  complianceCheck(intent: IntentAnalysis): ComplianceResult;
}

export interface ComplianceResult {
  isCompliant: boolean;
  violations: ComplianceViolation[];
  recommendations: string[];
  riskLevel: 'low' | 'medium' | 'high';
}

export interface ComplianceViolation {
  type: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  remediation: string;
}
