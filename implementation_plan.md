# Implementation Plan

Transform Open WebUI into OrcaAI Real Estate Assistant through Cloudflare Agents integration, achieving 95% codebase reduction while maintaining full real estate workflow automation.

This implementation follows a strategic migration approach, converting the existing heavy Python ML infrastructure into a lightweight Cloudflare Workers-based system with Google Workspace integration and specialized AI agents for real estate workflows.

## Overview

The OrcaAI implementation represents a fundamental architectural transformation from a monolithic Python-based AI platform to a distributed, serverless real estate assistant. This migration leverages Cloudflare Agents SDK for orchestration, GLM-4.5-Air for AI reasoning, and Google Workspace APIs for complete workflow automation.

The current Open WebUI system (6.5GB) will be transformed into OrcaAI (350MB) through:
- Replacement of heavy Python ML infrastructure with lightweight Cloudflare Agents
- Integration of specialized real estate workflow automation
- Maintaining existing chat interface while adding real estate-specific features
- Achieving sub-500ms AI response times through edge computing

## Types

### Core Agent Interfaces
```typescript
// src/agents/core/Agent.ts
interface Agent {
  id: string;
  name: string;
  version: string;
  initialize(config: AgentConfig): Promise<void>;
  handleMessage(message: string, context: AgentContext): Promise<AgentResponse>;
  cleanup(): Promise<void>;
}

interface AgentConfig {
  aiModel: string;
  apiKeys: Record<string, string>;
  rateLimits: RateLimitConfig;
  caching: CacheConfig;
}

interface AgentContext {
  userId: string;
  sessionId: string;
  timestamp: number;
  metadata: Record<string, any>;
}

interface AgentResponse {
  success: boolean;
  content: string;
  actions: AgentAction[];
  error?: string;
  confidence: number;
}

interface AgentAction {
  type: 'email' | 'calendar' | 'crm' | 'document' | 'api_call';
  payload: Record<string, any>;
  priority: 'low' | 'medium' | 'high' | 'urgent';
}
```

### Real Estate Domain Types
```typescript
// src/types/real-estate.ts
interface Lead {
  id: string;
  name: string;
  email: string;
  phone?: string;
  budget: number;
  preferences: PropertyPreferences;
  timeline: string;
  source: LeadSource;
  score: number; // 0-1 lead quality score
  status: LeadStatus;
  createdAt: Date;
  updatedAt: Date;
}

interface Property {
  id: string;
  address: string;
  price: number;
  bedrooms: number;
  bathrooms: number;
  squareFeet: number;
  type: PropertyType;
  features: string[];
  mlsId?: string;
  images: string[];
  description: string;
  location: GeoLocation;
  status: PropertyStatus;
}

interface Showing {
  id: string;
  propertyId: string;
  leadId: string;
  agentId: string;
  scheduledTime: Date;
  duration: number; // minutes
  status: ShowingStatus;
  notes?: string;
  participants: Participant[];
  reminders: Reminder[];
}

interface PropertyPacket {
  id: string;
  propertyId: string;
  leadId: string;
  documents: Document[];
  shareLink: string;
  createdAt: Date;
  expiresAt?: Date;
}
```

### AI Intent Types
```typescript
// src/types/intent.ts
interface IntentAnalysis {
  primaryAction: RealEstateAction;
  entities: IntentEntities;
  confidence: number;
  suggestedResponses: string[];
  requiredParameters: string[];
}

type RealEstateAction = 
  | 'email_check'
  | 'schedule_showing'
  | 'crm_update'
  | 'document_request'
  | 'property_search'
  | 'lead_qualification'
  | 'follow_up_sequence'
  | 'market_analysis';

interface IntentEntities {
  buyerName?: string;
  propertyAddress?: string;
  date?: Date;
  time?: string;
  budget?: number;
  preferences?: PropertyPreferences;
  urgency?: 'low' | 'medium' | 'high';
}
```

## Files

### New Files to Create

#### Cloudflare Workers Infrastructure
```
workers/
├── src/
│   ├── agents/
│   │   ├── OrcaOrchestrationAgent.ts
│   │   ├── gmail/
│   │   │   ├── GmailAgent.ts
│   │   │   ├── LeadProcessor.ts
│   │   │   └── EmailResponseGenerator.ts
│   │   ├── crm/
│   │   │   ├── CRMSheetsAgent.ts
│   │   │   ├── LeadManager.ts
│   │   │   └── PipelineManager.ts
│   │   ├── calendar/
│   │   │   ├── CalendarAgent.ts
│   │   │   ├── Scheduler.ts
│   │   │   └── AvailabilityChecker.ts
│   │   └── drive/
│   │       ├── DriveAgent.ts
│   │       ├── DocumentGenerator.ts
│   │       └── PropertyPacketCreator.ts
│   ├── ai/
│   │   ├── GLMClient.ts
│   │   ├── IntentAnalyzer.ts
│   │   └── ResponseGenerator.ts
│   ├── auth/
│   │   ├── OAuthManager.ts
│   │   └── TokenManager.ts
│   ├── storage/
│   │   ├── DurableObjectStorage.ts
│   │   └── CacheManager.ts
│   ├── types/
│   │   ├── agents.ts
│   │   ├── real-estate.ts
│   │   └── intent.ts
│   ├── utils/
│   │   ├── GoogleAPI.ts
│   │   ├── RateLimiter.ts
│   │   └── ErrorHandler.ts
│   └── index.ts
├── wrangler.toml
├── package.json
└── tsconfig.json
```

#### Frontend Agent Components
```
src/lib/components/agents/
├── OrcaChatInterface.svelte
├── PropertyCard.svelte
├── LeadStatusIndicator.svelte
├── CalendarView.svelte
└── DocumentViewer.svelte

src/lib/stores/
├── agentStore.ts
├── realEstateStore.ts
└── sessionStore.ts

src/lib/apis/agents/
├── index.ts
├── gmail.ts
├── crm.ts
├── calendar.ts
└── drive.ts
```

#### Test Files (TDD Approach)
```
tests/
├── agents/
│   ├── OrcaOrchestrationAgent.test.ts
│   ├── gmail/
│   │   ├── GmailAgent.test.ts
│   │   ├── LeadProcessor.test.ts
│   │   └── EmailResponseGenerator.test.ts
│   ├── crm/
│   │   ├── CRMSheetsAgent.test.ts
│   │   ├── LeadManager.test.ts
│   │   └── PipelineManager.test.ts
│   ├── calendar/
│   │   ├── CalendarAgent.test.ts
│   │   ├── Scheduler.test.ts
│   │   └── AvailabilityChecker.test.ts
│   └── drive/
│       ├── DriveAgent.test.ts
│       ├── DocumentGenerator.test.ts
│       └── PropertyPacketCreator.test.ts
├── ai/
│   ├── GLMClient.test.ts
│   ├── IntentAnalyzer.test.ts
│   └── ResponseGenerator.test.ts
├── integration/
│   ├── EndToEndWorkflow.test.ts
│   └── AgentCoordination.test.ts
└── e2e/
    ├── RealEstateWorkflow.test.ts
    └── Performance.test.ts
```

### Existing Files to Modify

#### Frontend Integration
```typescript
// src/routes/+layout.svelte
// Add agent store initialization and real estate components

// src/lib/apis/index.ts
// Add agent API endpoints

// src/app.html
// Add real estate specific meta tags and PWA configuration

// package.json
// Add Cloudflare Workers SDK and Google API dependencies
```

#### Configuration Files
```typescript
// wrangler.toml (new)
// Cloudflare Workers configuration

// .env.example
// Add Google OAuth and AI model API keys

// vite.config.ts
// Add proxy configuration for Cloudflare Workers during development
```

### Files to Phase Out (Migration Strategy)
```
backend/open_webui/routers/ollama.py
backend/open_webui/routers/openai.py
backend/open_webui/models/models.py
backend/requirements-fixed.txt (replace with worker dependencies)
```

## Functions

### New Functions to Implement

#### Core Orchestration
```typescript
// workers/src/agents/OrcaOrchestrationAgent.ts
async function handleMessage(message: string, context: AgentContext): Promise<AgentResponse> {
  // 1. Analyze intent using GLM-4.5-Air
  const intent = await this.aiClient.analyzeIntent(message);
  
  // 2. Route to specialized agent
  const agent = this.routeToAgent(intent.primaryAction);
  
  // 3. Execute agent workflow
  const response = await agent.execute(intent, context);
  
  // 4. Coordinate multi-agent workflows if needed
  if (response.requiresCoordination) {
    return await this.coordinateWorkflow(response, context);
  }
  
  return response;
}

async function routeToAgent(action: RealEstateAction): Promise<Agent> {
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
```

#### AI Model Integration
```typescript
// workers/src/ai/GLMClient.ts
async function analyzeIntent(query: string): Promise<IntentAnalysis> {
  const prompt = `Analyze this real estate assistant query and return JSON:
  Query: "${query}"
  Format: {
    "primaryAction": "action_type",
    "entities": {...},
    "confidence": 0.95,
    "suggestedResponses": ["response1", "response2"],
    "requiredParameters": ["param1", "param2"]
  }`;

  const response = await this.openRouter.chat.completions.create({
    model: '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',
    messages: [{ role: 'user', content: prompt }],
    temperature: 0.3,
    max_tokens: 1000
  });

  return JSON.parse(response.choices[0].message.content);
}

async function generateResponse(context: ResponseContext): Promise<string> {
  const prompt = `Generate a professional real estate response:
  Context: ${JSON.stringify(context)}
  Agent: ${context.agentName}
  Requirements: Personalized, professional, include next steps`;
  
  const response = await this.openRouter.chat.completions.create({
    model: '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',
    messages: [{ role: 'user', content: prompt }],
    temperature: 0.4
  });
  
  return response.choices[0].message.content;
}
```

#### Gmail Agent Functions
```typescript
// workers/src/agents/gmail/GmailAgent.ts
async function scanPropertyInquiries(timeframe: string): Promise<Email[]> {
  const query = this.buildGmailQuery(timeframe);
  const messages = await this.gmailAPI.listMessages({ q: query });
  
  return Promise.all(
    messages.map(message => this.processEmail(message))
  );
}

async function extractLeadInfo(email: Email): Promise<Lead> {
  const content = `${email.subject} ${email.body}`;
  const analysis = await this.aiClient.analyzeIntent(content);
  
  return {
    id: generateId(),
    name: analysis.entities.buyerName || this.extractName(email),
    email: email.from,
    phone: this.extractPhone(email.body),
    budget: analysis.entities.budget || this.extractBudget(email.body),
    preferences: analysis.entities.preferences || {},
    timeline: analysis.entities.timeline || 'unknown',
    source: 'email',
    score: this.calculateLeadScore(analysis),
    status: 'new',
    createdAt: new Date(),
    updatedAt: new Date()
  };
}

async function generateResponse(lead: Lead, inquiryType: string): Promise<Email> {
  const context = {
    agentName: 'OrcaAI',
    lead,
    inquiryType,
    property: lead.preferences.property || {}
  };
  
  const content = await this.aiClient.generateResponse(context);
  
  return {
    to: lead.email,
    subject: this.generateSubject(lead, inquiryType),
    body: content,
    priority: 'normal'
  };
}
```

#### CRM Agent Functions
```typescript
// workers/src/agents/crm/CRMSheetsAgent.ts
async function createLead(lead: Lead): Promise<void> {
  await this.sheetsAPI.appendValues({
    spreadsheetId: this.config.crmSheetId,
    range: 'Leads!A:J',
    values: [[
      lead.name,
      lead.email,
      lead.phone,
      lead.budget,
      JSON.stringify(lead.preferences),
      lead.timeline,
      lead.score,
      lead.status,
      lead.source,
      lead.createdAt.toISOString()
    ]]
  });
  
  // Create property-specific tracking
  if (lead.preferences.property) {
    await this.createPropertyTracking(lead.preferences.property);
  }
}

async function updateLeadStatus(leadId: string, status: LeadStatus): Promise<void> {
  const row = await this.findLeadRow(leadId);
  await this.sheetsAPI.updateValues({
    spreadsheetId: this.config.crmSheetId,
    range: `Leads!H${row}:H${row}`,
    values: [[status]]
  });
}

async function getPipelineAnalytics(): Promise<PipelineAnalytics> {
  const leads = await this.getAllLeads();
  return {
    totalLeads: leads.length,
    newLeads: leads.filter(l => l.status === 'new').length,
    qualifiedLeads: leads.filter(l => l.status === 'qualified').length,
    conversionRate: this.calculateConversionRate(leads),
    averageLeadScore: this.calculateAverageScore(leads),
    topSources: this.getTopSources(leads)
  };
}
```

#### Calendar Agent Functions
```typescript
// workers/src/agents/calendar/CalendarAgent.ts
async function scheduleShowing(request: ShowingRequest): Promise<Showing> {
  const availability = await this.checkAvailability(request);
  
  if (!availability.available) {
    throw new Error('Time slot not available');
  }
  
  const event = await this.createCalendarEvent({
    summary: `Property Showing: ${request.property.address}`,
    description: this.generateEventDescription(request),
    start: request.scheduledTime,
    end: new Date(request.scheduledTime.getTime() + request.duration * 60000),
    attendees: [request.lead.email, request.agent.email],
    location: request.property.address
  });
  
  const showing = {
    id: generateId(),
    propertyId: request.property.id,
    leadId: request.lead.id,
    agentId: request.agent.id,
    scheduledTime: request.scheduledTime,
    duration: request.duration,
    status: 'scheduled',
    participants: request.participants,
    reminders: this.generateReminders(event)
  };
  
  await this.crmAgent.logShowing(showing);
  return showing;
}

async function checkAvailability(date: Date): Promise<AvailabilityResponse> {
  const events = await this.calendarAPI.listEvents({
    timeMin: date,
    timeMax: new Date(date.getTime() + 24 * 60 * 60 * 1000),
    singleEvents: true,
    orderBy: 'startTime'
  });
  
  const conflicts = events.filter(event => 
    this.isTimeConflict(event, date)
  );
  
  return {
    available: conflicts.length === 0,
    conflicts: conflicts.map(c => c.summary),
    suggestedAlternatives: conflicts.length > 0 ? 
      await this.findAlternativeSlots(date) : []
  };
}
```

#### Drive Agent Functions
```typescript
// workers/src/agents/drive/DriveAgent.ts
async function createPropertyPacket(property: Property, lead: Lead): Promise<PropertyPacket> {
  const folder = await this.createPropertyFolder(property);
  
  const documents = await Promise.all([
    this.generatePropertySummary(property),
    this.generateCoverLetter(lead, property),
    this.retrieveMLSDocuments(property),
    this.createDisclosureForms(property, lead)
  ]);
  
  const packet = {
    id: generateId(),
    propertyId: property.id,
    leadId: lead.id,
    documents,
    shareLink: await this.generateShareLink(folder.id, lead.email),
    createdAt: new Date(),
    expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) // 7 days
  };
  
  await this.crmAgent.logDocumentPacket(packet);
  return packet;
}

async function generatePropertySummary(property: Property): Promise<Document> {
  const content = await this.aiClient.generateResponse({
    agentName: 'OrcaAI',
    property,
    template: 'property_summary'
  });
  
  return this.createDocument({
    name: `${property.address} - Property Summary.pdf`,
    content,
    folderId: property.folderId
  });
}
```

### Modified Functions

#### Frontend Chat Integration
```typescript
// src/lib/components/chat/ChatInterface.svelte
async function sendMessage(message: string) {
  // Add real estate intent detection
  const isRealEstateQuery = await detectRealEstateIntent(message);
  
  if (isRealEstateQuery) {
    // Route to OrcaAI agents
    const response = await orcaAgent.sendMessage(message);
    displayRealEstateResponse(response);
  } else {
    // Route to existing Open WebUI system
    const response = await openWebui.sendMessage(message);
    displayStandardResponse(response);
  }
}
```

#### API Routing
```typescript
// src/lib/apis/index.ts
export async function sendToOrcaAgent(message: string, userId: string) {
  const response = await fetch(`${WORKER_URL}/agents/orchestrate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getAuthToken()}`
    },
    body: JSON.stringify({
      message,
      userId,
      sessionId: getCurrentSession()
    })
  });
  
  return response.json();
}
```

## Classes

### New Core Classes

#### OrcaOrchestrationAgent
```typescript
// workers/src/agents/OrcaOrchestrationAgent.ts
export class OrcaOrchestrationAgent implements Agent {
  private gmailAgent: GmailAgent;
  private crmAgent: CRMSheetsAgent;
  private calendarAgent: CalendarAgent;
  private driveAgent: DriveAgent;
  private aiClient: GLMClient;
  private storage: DurableObjectStorage;
  
  constructor(config: OrcaConfig) {
    this.aiClient = new GLMClient(config.ai);
    this.gmailAgent = new GmailAgent(config.gmail);
    this.crmAgent = new CRMSheetsAgent(config.crm);
    this.calendarAgent = new CalendarAgent(config.calendar);
    this.driveAgent = new DriveAgent(config.drive);
    this.storage = new DurableObjectStorage(config.storage);
  }
  
  async initialize(): Promise<void> {
    await Promise.all([
      this.aiClient.initialize(),
      this.gmailAgent.initialize(),
      this.crmAgent.initialize(),
      this.calendarAgent.initialize(),
      this.driveAgent.initialize()
    ]);
  }
  
  async handleMessage(message: string, context: AgentContext): Promise<AgentResponse> {
    try {
      const intent = await this.aiClient.analyzeIntent(message);
      const agent = this.routeToAgent(intent.primaryAction);
      
      const response = await agent.handleMessage(intent, context);
      
      // Store conversation history
      await this.storage.storeConversation({
        userId: context.userId,
        message,
        intent,
        response,
        timestamp: Date.now()
      });
      
      return response;
    } catch (error) {
      return this.handleError(error, context);
    }
  }
  
  private async coordinateWorkflow(response: AgentResponse, context: AgentContext): Promise<AgentResponse> {
    // Implement multi-agent coordination for complex workflows
    const workflow = new WorkflowCoordinator(this);
    return await workflow.execute(response, context);
  }
}
```

#### GmailAgent
```typescript
// workers/src/agents/gmail/GmailAgent.ts
export class GmailAgent implements Agent {
  private gmailAPI: GmailAPI;
  private aiClient: GLMClient;
  private rateLimiter: RateLimiter;
  
  constructor(config: GmailConfig) {
    this.gmailAPI = new GmailAPI(config.oauth);
    this.aiClient = new GLMClient(config.ai);
    this.rateLimiter = new RateLimiter(config.rateLimits);
  }
  
  async scanPropertyInquiries(timeframe: string): Promise<Lead[]> {
    await this.rateLimiter.waitForToken();
    
    const query = `subject:(property OR house OR home OR real estate) after:${this.getTimeframeDate(timeframe)}`;
    const messages = await this.gmailAPI.listMessages({ q: query, maxResults: 50 });
    
    const leads: Lead[] = [];
    for (const message of messages) {
      const email = await this.getEmail(message.id);
      const lead = await this.extractLeadInfo(email);
      
      if (lead.score > 0.7) { // High-quality leads only
        leads.push(lead);
      }
    }
    
    return leads;
  }
  
  async processEmails(intent: IntentAnalysis, context: AgentContext): Promise<AgentResponse> {
    const emails = await this.scanPropertyInquiries('last_24h');
    const processedLeads: Lead[] = [];
    
    for (const email of emails) {
      const lead = await this.extractLeadInfo(email);
      await this.crmAgent.createLead(lead);
      processedLeads.push(lead);
      
      // Send auto-response
      const response = await this.generateResponse(lead, 'property_inquiry');
      await this.sendEmail(response);
    }
    
    return {
      success: true,
      content: `Processed ${processedLeads.length} property inquiries. Created ${processedLeads.length} new leads in CRM.`,
      actions: processedLeads.map(lead => ({
        type: 'crm',
        payload: { action: 'lead_created', leadId: lead.id },
        priority: 'medium'
      })),
      confidence: 0.95
    };
  }
}
```

#### GLMClient
```typescript
// workers/src/ai/GLMClient.ts
export class GLMClient {
  private openRouter: OpenRouterAPI;
  private cache: CacheManager;
  
  constructor(config: AIConfig) {
    this.openRouter = new OpenRouterAPI({
      apiKey: config.apiKey,
      baseURL: config.baseURL
    });
    this.cache = new CacheManager(config.cache);
  }
  
  async analyzeIntent(query: string): Promise<IntentAnalysis> {
    const cacheKey = `intent:${hash(query)}`;
    const cached = await this.cache.get(cacheKey);
    
    if (cached) {
      return cached;
    }
    
    const prompt = `Analyze this real estate assistant query:
    Query: "${query}"
    
    Return JSON with:
    - primaryAction: Main action type
    - entities: Extracted entities (names, addresses, dates, etc.)
    - confidence: 0-1 confidence score
    - suggestedResponses: 2-3 appropriate response options
    - requiredParameters: Missing information needed`;
    
    const response = await this.openRouter.chat.completions.create({
      model: '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',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.3,
      max_tokens: 1000
    });
    
    const analysis: IntentAnalysis = JSON.parse(response.choices[0].message.content);
    
    // Cache for 1 hour
    await this.cache.set(cacheKey, analysis, 3600);
    
    return analysis;
  }
  
  async generateResponse(context: ResponseContext): Promise<string> {
    const prompt = `Generate a professional real estate response:
    
    Agent: ${context.agentName}
    Lead: ${context.lead.name} (${context.lead.email})
    Property: ${context.property?.address || 'TBD'}
    Inquiry Type: ${context.inquiryType}
    
    Requirements:
    - Personalized greeting using lead name
    - Address their specific inquiry
    - Include relevant property details if available
    - Provide clear next steps
    - Professional closing with contact information
    - Keep under 300 words`;
    
    const response = await this.openRouter.chat.completions.create({
      model: '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',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.4,
      max_tokens: 800
    });
    
    return response.choices[0].message.content;
  }
}
```

### Modified Classes

#### Frontend Store Integration
```typescript
// src/lib/stores/agentStore.ts
export class AgentStore {
  private orcaAgent: OrcaAgentClient;
  private realEstateData: RealEstateStore;
  
  constructor() {
    this.orcaAgent = new OrcaAgentClient();
    this.realEstateData = new RealEstateStore();
  }
  
  async sendRealEstateMessage(message: string): Promise<AgentResponse> {
    const response = await this.orcaAgent.sendMessage(message);
    
    // Update real estate data based on response
    if (response.actions) {
      await this.processAgentActions(response.actions);
    }
    
    return response;
  }
  
  private async processAgentActions(actions: AgentAction[]): Promise<void> {
    for (const action of actions) {
      switch (action.type) {
        case 'crm':
          await this.realEstateData.updateCRM(action.payload);
          break;
        case 'calendar':
          await this.realEstateData.updateCalendar(action.payload);
          break;
        case 'document':
          await this.realEstateData.updateDocuments(action.payload);
          break;
      }
    }
  }
}
```

## Dependencies

### New Dependencies

#### Cloudflare Workers
```json
// workers/package.json
{
  "name": "orcaai-workers",
  "version": "1.0.0",
  "type": "module",
  "dependencies": {
    "@cloudflare/agents-sdk": "^1.0.0",
    "@googleapis/gmail": "^9.0.0",
    "@googleapis/sheets": "^9.0.0",
    "@googleapis/calendar": "^9.0.0",
    "@googleapis/drive": "^9.0.0",
    "google-auth-library": "^9.0.0",
    "openai": "^4.0.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0",
    "wrangler": "^3.0.0"
  },
  "devDependencies": {
    "@cloudflare/workers-types": "^4.0.0",
    "typescript": "^5.0.0",
    "vitest": "^1.0.0",
    "@types/googleapis": "^128.0.0"
  }
}
```

#### Frontend Dependencies
```json
// package.json (additions)
{
  "dependencies": {
    "@google-cloud/oauth2": "^4.0.0",
    "date-fns": "^3.0.0",
    "framer-motion": "^10.0.0",
    "recharts": "^2.0.0"
  }
}
```

### Version Changes

#### Remove Heavy Dependencies
```json
// package.json (removals)
{
  "dependencies": {
    // Remove heavy ML libraries
    "@huggingface/transformers": "^3.0.0",
    "pyodide": "^0.28.2",
    // Remove unused charting libraries
    "chart.js": "^4.5.0",
    // Replace with lighter alternatives
  }
}
```

#### Backend Migration
```json
// workers/wrangler.toml
name = "orcaai-workers"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[env.production]
vars = { ENVIRONMENT = "production" }

[env.staging]
vars = { ENVIRONMENT = "staging" }

[[env.production.kv_namespaces]]
binding = "ORCA_STORAGE"
id = "your-kv-namespace-id"

[[env.production.durable_objects]]
bindings = [
  { name = "SESSION_STORE", class_name = "SessionStore" },
  { name = "CACHE_STORE", class_name = "CacheStore" }
]
```

## Testing

### TDD Test Structure

#### Unit Tests (Red-Green-Refactor)
```typescript
// tests/agents/OrcaOrchestrationAgent.test.ts
describe('OrcaOrchestrationAgent', () => {
  let agent: OrcaOrchestrationAgent;
  let mockAI: MockGLMClient;
  let mockGmail: MockGmailAgent;
  
  beforeEach(() => {
    mockAI = new MockGLMClient();
    mockGmail = new MockGmailAgent();
    agent = new OrcaOrchestrationAgent({
      ai: mockAI,
      gmail: mockGmail
    });
  });
  
  // RED PHASE - Write failing test first
  test('should route email queries to GmailAgent', async () => {
    const message = "Check my emails for property inquiries";
    const context = createMockContext();
    
    // Test should fail initially
    const response = await agent.handleMessage(message, context);
    
    expect(mockGmail.processEmails).toHaveBeenCalledWith(
      expect.objectContaining({
        primaryAction: 'email_check'
      })
    );
  });
  
  // GREEN PHASE - Minimal implementation to pass
  test('should return successful response for valid email query', async () => {
    mockAI.analyzeIntent.mockResolvedValue({
      primaryAction: 'email_check',
      confidence: 0.95
    });
    
    mockGmail.processEmails.mockResolvedValue({
      success: true,
      content: 'Processed 5 emails',
      actions: []
    });
    
    const response = await agent.handleMessage('Check emails', createMockContext());
    
    expect(response.success).toBe(true);
    expect(response.content).toContain('5 emails');
  });
  
  // REFACTOR PHASE - Improve implementation
  test('should handle agent failures gracefully', async () => {
    mockAI.analyzeIntent.mockResolvedValue({
      primaryAction: 'email_check',
      confidence: 0.95
    });
    
    mockGmail.processEmails.mockRejectedValue(new Error('Gmail API down'));
    
    const response = await agent.handleMessage('Check emails', createMockContext());
    
    expect(response.success).toBe(false);
    expect(response.error).toContain('Gmail API');
    expect(response.alternativeActions).toBeDefined();
  });
});
```

#### Integration Tests
```typescript
// tests/integration/EndToEndWorkflow.test.ts
describe('End-to-End Real Estate Workflow', () => {
  test('should complete lead intake to showing workflow', async () => {
    // 1. Email received
    const email = createMockPropertyInquiryEmail();
    await gmailAgent.receiveEmail(email);
    
    // 2. Lead extracted and created
    const lead = await crmAgent.getLeadByEmail(email.from);
    expect(lead).toBeDefined();
    expect(lead.score).toBeGreaterThan(0.8);
    
    // 3. Showing scheduled
    const showingRequest = {
      property: createMockProperty(),
      lead,
      agent: createMockAgent(),
      date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000) // 2 days from now
    };
    
    const showing = await calendarAgent.scheduleShowing(showingRequest);
    expect(showing.status).toBe('scheduled');
    
    // 4. Property packet generated
    const packet = await driveAgent.createPropertyPacket(showingRequest.property, lead);
    expect(packet.documents.length).toBeGreaterThan(3);
    expect(packet.shareLink).toBeDefined();
    
    // 5. Confirmation emails sent
    expect(gmailAgent.sentConfirmationEmails).toHaveLength(2); // Lead and agent
  });
});
```

#### Performance Tests
```typescript
// tests/e2e/Performance.test.ts
describe('Performance Requirements', () => {
  test('AI intent analysis should complete within 500ms', async () => {
    const startTime = Date.now();
    await aiClient.analyzeIntent('Schedule showing for Sarah tomorrow at 2 PM');
    const duration = Date.now() - startTime;
    
    expect(duration).toBeLessThan(500);
  });
  
  test('Email processing should handle 50 concurrent requests', async () => {
    const requests = Array(50).fill().map(() => 
      gmailAgent.scanPropertyInquiries('last_24h')
    );
    
    const results = await Promise.all(requests);
    const successRate = results.filter(r => r.success).length / results.length;
    
    expect(successRate).toBeGreaterThan(0.95);
  });
  
  test('Memory usage should stay below 128MB for worker', async () => {
    // This would require memory profiling in actual Cloudflare environment
    const memoryUsage = await getWorkerMemoryUsage();
    expect(memoryUsage).toBeLessThan(128 * 1024 * 1024); // 128MB
  });
});
```

### Test Coverage Requirements
- **Unit Tests**: 95% coverage for all agent classes
- **Integration Tests**: 100% coverage for cross-agent workflows
- **E2E Tests**: All major user stories covered
- **Performance Tests**: All SLA requirements validated
- **Security Tests**: OAuth flows and data access patterns tested

## Implementation Order

### Phase 1: Foundation & Cloudflare Setup (Week 1)
1. **Set up Cloudflare Workers development environment**
   - Install Wrangler CLI and configure Cloudflare account
   - Create worker project structure
   - Set up KV namespaces and Durable Objects

2. **Implement core Agent interfaces and base classes**
   - Create Agent interface and abstract base class
   - Implement AgentContext and AgentResponse types
   - Set up error handling and logging framework

3. **Configure Google Workspace OAuth integration**
   - Set up OAuth 2.0 credentials in Google Cloud Console
   - Implement token management and refresh logic
   - Create API client wrappers for Gmail, Sheets, Calendar, Drive

4. **Implement GLM-4.5-Air AI client**
   - Integrate with Open Router API using provided model key
   - Implement intent analysis and response generation
   - Add caching and rate limiting

### Phase 2: AI Model Integration & Orchestration (Week 2)
5. **Create OrcaOrchestrationAgent**
   - Implement agent routing logic based on intent analysis
   - Set up multi-agent coordination framework
   - Add conversation history storage in Durable Objects

6. **Implement intent analysis system**
   - Create comprehensive real estate intent classification
   - Add entity extraction for addresses, names, dates, budgets
   - Implement confidence scoring and validation

7. **Build response generation framework**
   - Create templates for different real estate scenarios
   - Implement personalization based on lead and property data
   - Add professional tone and brand voice consistency

8. **Set up caching and performance optimization**
   - Implement KV-based caching for AI responses
   - Add rate limiting for API calls
   - Optimize for sub-500ms response times

### Phase 3: Gmail Agent Implementation (Week 3)
9. **Build GmailAgent core functionality**
   - Implement email scanning and filtering for property inquiries
   - Create lead information extraction using AI analysis
   - Add automated response generation and sending

10. **Implement lead processing pipeline**
    - Create lead qualification scoring algorithm
    - Add duplicate detection and merging logic
    - Implement CRM integration for lead creation

11. **Build email campaign automation**
    - Create follow-up sequence scheduling
    - Add personalized content generation
    - Implement open rate and engagement tracking

12. **Add email performance monitoring**
    - Create metrics for response times and success rates
    - Implement error handling and retry logic
    - Add logging and analytics integration

### Phase 4: CRM Agent Implementation (Week 4)
13. **Build CRMSheetsAgent for Google Sheets integration**
    - Implement lead CRUD operations in Google Sheets
    - Create property tracking and management
    - Add deal pipeline visualization and management

14. **Implement automated lead management**
    - Create lead scoring and progression algorithms
    - Add intelligent next-action suggestions
    - Build activity tracking and logging

15. **Build CRM intelligence dashboard**
    - Implement real-time pipeline analytics
    - Create performance metrics calculation
    - Add predictive analytics and recommendations

16. **Implement CRM synchronization engine**
    - Create bidirectional data synchronization
    - Add conflict resolution and data validation
    - Implement offline sync capabilities

### Phase 5: Calendar Agent Implementation (Week 5)
17. **Build CalendarAgent for scheduling automation**
    - Implement availability checking and conflict detection
    - Create multi-party appointment coordination
    - Add automated invitation generation

18. **Implement intelligent scheduling workflows**
    - Create optimization algorithms for time slot selection
    - Add travel time calculations and location awareness
    - Build reminder systems and notifications

19. **Build appointment management system**
    - Create preparation checklist automation
    - Implement client communication sequences
    - Add outcome tracking and follow-up automation

20. **Add calendar intelligence features**
    - Implement productivity pattern analysis
    - Create scheduling optimization recommendations
    - Add revenue correlation tracking

### Phase 6: Drive Agent Implementation (Week 6)
21. **Build DriveAgent for document management**
    - Implement intelligent document organization
    - Create automated folder hierarchy generation
    - Add file naming standardization and tagging

22. **Implement property packet generation**
    - Create MLS data integration and retrieval
    - Build branded document template system
    - Add comprehensive property packet compilation

23. **Build client document sharing system**
    - Implement secure permission-based access control
    - Create usage tracking and reporting
    - Add expiration and renewal automation

24. **Add document intelligence capabilities**
    - Implement contract analysis and summarization
    - Create financial document processing
    - Add automated form filling and risk assessment

### Phase 7: Integration & Optimization (Week 7-8)
25. **Frontend integration and UI development**
    - Create OrcaAI chat interface components
    - Implement real estate-specific UI elements
    - Add property cards, lead indicators, and calendar views

26. **End-to-end workflow testing**
    - Implement comprehensive integration tests
    - Validate all user stories and acceptance criteria
    - Performance test under realistic load conditions

27. **Security and compliance validation**
    - Implement data encryption and privacy controls
    - Add audit logging and monitoring
    - Validate GDPR/HIPAA compliance requirements

28. **Production deployment and monitoring**
    - Deploy to Cloudflare Workers edge network
    - Set up monitoring and alerting
    - Create documentation and training materials

### Success Metrics
- **Performance**: <500ms AI response times, 99.9% uptime
- **Quality**: 95%+ intent classification accuracy, 98%+ scheduling success
- **User Experience**: 90%+ task completion rate, 4.5/5 user satisfaction
- **Business Impact**: 80% reduction in administrative time, 40% increase in lead response speed

This implementation plan follows true TDD principles, with comprehensive test coverage and a strategic migration approach that maintains existing functionality while building the new OrcaAI system.
