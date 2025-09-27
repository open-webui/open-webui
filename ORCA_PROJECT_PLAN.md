# 🏗️ OrcaAI Real Estate Assistant - Project Implementation Plan

**Version:** 1.0
**Based on:** ORCA_REAL_ESTATE_AI_PRD.md
**Date:** September 26, 2025
**Approach:** Test-Driven Development (TDD)

---

## 🎯 Project Overview

**OrcaAI** transforms Open WebUI into a complete real estate AI assistant that automates workflows through Google Workspace integration. This project plan breaks down the PRD into **TDD-driven user stories** with detailed acceptance criteria, code samples, and testing requirements.

**Total Estimated Effort:** 12 weeks
**Total User Stories:** 28
**TDD Approach:** Red-Green-Refactor cycle for each story

---

## 📋 Project Structure

### **Epic 1: Foundation & Infrastructure (Weeks 1-3)**
User Stories 1-8: Core architecture, authentication, basic chat interface

### **Epic 2: AI Model Integration (Weeks 1-2)***
User Stories 9-12: GLM-4.5-Air + Open Router + Cloudflare Agents

### **Epic 3: Gmail Agent (Weeks 3-4)**
User Stories 13-16: Email processing, lead extraction, response generation

### **Epic 4: CRM Agent (Weeks 4-5)**
User Stories 17-20: Google Sheets integration, lead management

### **Epic 5: Calendar Agent (Weeks 5-6)**
User Stories 21-24: Scheduling automation, availability checking

### **Epic 6: Drive Agent (Weeks 6-7)**
User Stories 25-28: Document management, property packets

---

# 📖 **USER STORIES**

## **Epic 1: Foundation & Infrastructure**

### **US-001: OrcaAI Chat Authentication System**
**As a** real estate agent
**I want** secure authentication to OrcaAI
**So that** I can safely access my data and maintain privacy

**Description:**
Implement OAuth 2.0 flow for Google Workspace with role-based access control ensuring agents can only access their own data while maintaining HIPAA/GDPR compliance.

**Acceptance Criteria:**
- ✅ Google OAuth 2.0 PKCE flow implemented
- ✅ JWT tokens issued with agent-specific scopes
- ✅ Session storage in Cloudflare Durable Objects
- ✅ Automatic token refresh handling
- ✅ Privacy consent collection for data access

**TDD Test-First Code Sample:**
```typescript
// tests/auth/oauth.test.ts
describe('OAuth Flow', () => {
  test('should generate valid authorization URL', () => {
    const auth = new OAuthManager();
    const url = auth.getAuthorizationUrl({
      scopes: ['https://www.googleapis.com/auth/gmail.readonly']
    });

    expect(url).toContain('accounts.google.com');
    expect(url).toContain('state=');
    expect(url).toContain('scope=');
  });

  test('should validate and store access tokens', async () => {
    const token = await oauth.exchangeCodeForToken('valid_code');
    expect(token.access_token).toBeDefined();
    expect(token.scope).toContain('gmail.readonly');
  });
});

// src/agents/auth/OAuthManager.ts (Red phase - failing tests)
export class OAuthManager {
  getAuthorizationUrl(): string {
    throw new Error('Method not implemented');
  }
}

export class OAuthManager {
  getAuthorizationUrl(scopes: string[]): string {
    // Green phase - implement to pass tests
    const params = new URLSearchParams({
      client_id: process.env.GOOGLE_CLIENT_ID,
      redirect_uri: process.env.REDIRECT_URI,
      scope: scopes.join(' '),
      response_type: 'code',
      state: this.generateState()
    });
    return `https://accounts.google.com/o/oauth2/v2/auth?${params}`;
  }
}
```

---

### **US-002: Cloudflare Durable Objects Storage**
**As a** real estate agent
**I want** my conversation history persisted across sessions
**So that** OrcaAI remembers context and maintains continuity

**Description:**
Implement Cloudflare Durable Objects for session persistence, storing chat history, agent configurations, and intermediate workflow states with automatic cleanup policies.

**Acceptance Criteria:**
- ✅ Conversation threads stored for 90 days
- ✅ Agent preferences persisted per user
- ✅ Workflow state snapshots maintained
- ✅ Automatic cleanup of expired sessions
- ✅ Cross-device synchronization

**TDD Test-First Code Sample:**
```typescript
// tests/storage/durable-objects.test.ts
describe('Durable Objects Storage', () => {
  test('should store and retrieve conversation history', async () => {
    const storage = new DurableStorage();
    const session = { id: 'test-session', messages: [] };

    await storage.storeSession(session);
    const retrieved = await storage.getSession('test-session');

    expect(retrieved).toEqual(session);
  });

  test('should automatically cleanup expired sessions', async () => {
    const expiredSession = {
      id: 'expired',
      messages: [],
      createdAt: new Date(Date.now() - 91 * 24 * 60 * 60 * 1000) // 91 days ago
    };

    await storage.storeSession(expiredSession);
    await storage.cleanupExpired();

    await expect(storage.getSession('expired')).rejects.toThrow('Not found');
  });
});

// src/storage/DurableStorage.ts
export class DurableStorage {
  async storeSession(session: Session): Promise<void> {
    // Red phase - failing tests
    throw new Error('Not implemented');
  }

  async storeSession(session: Session): Promise<void> {
    // Green phase - implement for Durable Objects
    const doState = getDurableObjectState();
    await doState.storage.put(`session_${session.id}`, session);
  }
}
```

---

### **US-003: Open WebUI Chat Integration**
**As a** real estate agent
**I want** a familiar chat interface
**So that** I can interact with OrcaAI naturally

**Description:**
Adapt Open WebUI's chat components for OrcaAI workflow automation while maintaining the streaming chat experience and adding real estate-specific UI enhancements.

**Acceptance Criteria:**
- ✅ Preserved Open WebUI streaming chat functionality
- ✅ Property card components integrated
- ✅ Agent status indicators added
- ✅ Real estate terminology support
- ✅ Mobile-responsive design maintained

**TDD Test-First Code Sample:**
```typescript
// tests/ui/chat/ChatInterface.test.ts
describe('Chat Interface', () => {
  test('should render Open WebUI chat components', () => {
    render(<ChatInterface />);
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
    expect(screen.getByTestId('message-list')).toBeInTheDocument();
  });

  test('should display real estate property cards', () => {
    const propertyData = { address: '123 Main St', price: '$450K' };
    render(<PropertyCard {...propertyData} />);

    expect(screen.getByText('123 Main St')).toBeInTheDocument();
    expect(screen.getByText('$450K')).toBeInTheDocument();
  });

  test('should stream AI responses in real-time', () => {
    const mockStream = jest.fn();
    render(<ChatInterface onMessageStream={mockStream} />);

    const input = screen.getByTestId('chat-input');
    fireEvent.change(input, { target: { value: 'Schedule showing' } });
    fireEvent.click(screen.getByTestId('send-button'));

    expect(mockStream).toHaveBeenCalled();
  });
});

// src/components/chat/ChatInterface.svelte (Red phase)
<script>
  export let messages = [];
  export let streaming = false;

  function onMessageStream() {
    throw new Error('Not implemented');
  }
</script>

// src/components/chat/ChatInterface.svelte (Green phase)
<script>
  export let messages = [];
  export let streaming = false;

  function onMessageStream(chunk) {
    messages = [...messages, { content: chunk, streaming: true }];
  }
</script>

<div class="chat-interface">
  {#each messages as message}
    <MessageBubble {message} />
  {/each}
  {#if streaming}
    <TypingIndicator />
  {/if}
  <input bind:value={inputValue} on:keydown={handleSend} />
</div>
```

---

## **Epic 2: AI Model Integration**

### **US-009: GLM-4.5-Air Open Router Client**
**As a** real estate AI assistant
**I want** reliable intent analysis and response generation
**So that** I can understand natural language requests accurately

**Description:**
Implement Open Router client for GLM-4.5-Air model with structured prompt engineering optimized for real estate workflows, intent classification, and conversational responses.

**Acceptance Criteria:**
- ✅ Open Router API integration configured
- ✅ GLM-4.5-Air model responses within 500ms
- ✅ Structured real estate prompt templates
- ✅ Fallback to cached responses on failure
- ✅ Token usage optimization

**TDD Test-First Code Sample:**
```typescript
// tests/ai/glm-client.test.ts
describe('GLM-4.5-Air Client', () => {
  test('should analyze intent from natural language', async () => {
    const client = new GLMClient();
    const result = await client.analyzeIntent('Schedule a showing for Sarah tomorrow');

    expect(result.intent).toBe('schedule_showing');
    expect(result.entities.buyerName).toBe('Sarah');
    expect(result.entities.timeFrame).toBe('tomorrow');
  });

  test('should respond within 500ms for typical queries', async () => {
    const startTime = Date.now();
    const response = await glmClient.generateResponse('Create an offer letter');
    const duration = Date.now() - startTime;

    expect(duration).toBeLessThan(500);
    expect(response).toContain('offer');
  });

  test('should handle API failures gracefully', async () => {
    // Mock API failure
    jest.spyOn(global, 'fetch').mockRejectedValue(new Error('API down'));

    const response = await glmClient.generateResponse('Test query');
    expect(response).toBe('I apologize, I\'m having trouble connecting right now.');
  });
});

// src/ai/GLMClient.ts (Red phase)
export class GLMClient {
  async analyzeIntent(query: string) {
    throw new Error('Not implemented');
  }
}

// src/ai/GLMClient.ts (Green phase)
export class GLMClient {
  private openRouter: OpenRouterAPI;

  constructor() {
    this.openRouter = new OpenRouterAPI({
      apiKey: process.env.OPEN_ROUTER_API_KEY,
      model: 'z-ai/glm-4.5-air:free'
    });
  }

  async analyzeIntent(query: string) {
    const response = await this.openRouter.chat.completions.create({
      model: 'z-ai/glm-4.5-air:free',
      messages: [{
        role: 'user',
        content: `Analyze this real estate assistant query and return JSON: ${query}`
      }],
      temperature: 0.3
    });

    return JSON.parse(response.choices[0].message.content);
  }
}
```

---

### **US-010: Orchestration Agent Framework**
**As a** real estate AI assistant
**I want** coordinated multi-agent workflows
**So that** I can execute complex tasks across services

**Description:**
Build OrcaOrchestrationAgent that routes user requests to specialized agents (email, CRM, calendar, drive) and coordinates responses using GLM-4.5-Air for intelligent decision making.

**Acceptance Criteria:**
- ✅ Intent routing to appropriate specialized agents
- ✅ Sequential and parallel task execution
- ✅ Error handling and recovery
- ✅ Status tracking and user updates
- ✅ Context preservation across interactions

**TDD Test-First Code Sample:**
```typescript
// tests/agents/OrcaOrchestrationAgent.test.ts
describe('Orchestration Agent', () => {
  test('should route email queries to GmailAgent', async () => {
    const orchestrator = new OrcaOrchestrationAgent();
    const gmailSpy = jest.spyOn(orchestrator.gmailAgent, 'processEmails');

    await orchestrator.handleMessage('Check my emails for property inquiries');

    expect(gmailSpy).toHaveBeenCalledWith('property inquiries');
  });

  test('should coordinate multi-agent workflows', async () => {
    const orchestrator = new OrcaOrchestrationAgent();
    const result = await orchestrator.handleMessage(
      'Schedule showing for John at 123 Oak St'
    );

    expect(orchestrator.crmAgent.updateLead).toHaveBeenCalled();
    expect(orchestrator.calendarAgent.scheduleShowing).toHaveBeenCalled();
    expect(orchestrator.gmailAgent.sendConfirmation).toHaveBeenCalled();
    expect(result.success).toBe(true);
  });

  test('should handle agent failures gracefully', async () => {
    jest.spyOn(orchestrator.calendarAgent, 'scheduleShowing')
      .mockRejectedValue(new Error('Conflict detected'));

    const result = await orchestrator.handleMessage('Schedule showing tomorrow');

    expect(result.error).toContain('conflict');
    expect(result.alternativeTimes).toBeDefined();
  });
});

// src/agents/OrcaOrchestrationAgent.ts (Red phase)
export class OrcaOrchestrationAgent extends Agent {
  constructor() {
    super();
    // Initialize agents
  }

  async handleMessage(message: string, userId: string) {
    throw new Error('Orchestration not implemented');
  }
}

// src/agents/OrcaOrchestrationAgent.ts (Green phase)
export class OrcaOrchestrationAgent extends Agent {
  gmailAgent: GmailAgent;
  crmAgent: CRMSheetsAgent;
  calendarAgent: CalendarAgent;
  driveAgent: DriveAgent;
  llm: GLMClient;

  async handleMessage(message: string, userId: string): Promise<Response> {
    // 1. Analyze intent with GLM-4.5-Air
    const intent = await this.llm.analyzeIntent(message);

    // 2. Route to appropriate agent
    switch (intent.intent) {
      case 'email_check':
        return await this.gmailAgent.processEmails(intent);
      case 'schedule_showing':
        return await this.handleSchedulingWorkflow(intent);
      case 'crm_update':
        return await this.crmAgent.updateLead(intent);
      default:
        return await this.llm.generateResponse(message);
    }
  }

  private async handleSchedulingWorkflow(intent): Promise<Response> {
    // Coordinate multiple agents for complex workflows
    const [availability, leadInfo] = await Promise.all([
      this.calendarAgent.checkAvailability(intent.date),
      this.crmAgent.getLeadByName(intent.buyerName)
    ]);

    if (availability.available) {
      const event = await this.calendarAgent.scheduleShowing({
        propertyAddress: intent.property,
        buyerInfo: leadInfo,
        date: intent.date
      });

      await this.crmAgent.logActivity({
        type: 'showing_scheduled',
        leadId: leadInfo.id,
        eventId: event.id
      });

      return { success: true, event: event };
    }

    return { success: false, reason: 'time_conflict' };
  }
}
```

---

## **Epic 3: Gmail Agent**

### **US-013: Gmail Integration & API Client**
**As a** real estate agent
**I want** OrcaAI to access my email
**So that** I can automate lead intake and communication

**Description:**
Implement authenticated Gmail API access for scanning inbox, reading messages, extracting lead information, and sending responses through Google's secure OAuth flow.

**Acceptance Criteria:**
- ✅ Gmail API readonly access configured
- ✅ Rate-limited email scanning
- ✅ Property-related email detection
- ✅ Contact information extraction
- ✅ Secure token storage in Durable Objects

**TDD Test-First Code Sample:**
```typescript
// tests/agents/gmail/GmailAgent.test.ts
describe('Gmail Agent', () => {
  test('should scan inbox for property-related emails', async () => {
    const gmail = new GmailAgent();
    const emails = await gmail.scanPropertyEmails('last_24h');

    expect(emails).toHaveLength(3);
    emails.forEach(email => {
      expect(email.subject.toLowerCase()).toMatch(/(property|house|home)/i);
    });
  });

  test('should extract lead information from emails', async () => {
    const sampleEmail = {
      from: 'john@buyer.com',
      subject: 'Interest in 123 Oak Street',
      body: 'Looking for 3-bedroom house, budget $450K'
    };

    const lead = await gmailAgent.extractLead(sampleEmail);

    expect(lead.name).toBe('john');
    expect(lead.email).toBe('john@buyer.com');
    expect(lead.budget).toBe(450000);
    expect(lead.preferences).toContain('3-bedroom');
  });

  test('should rate limit Gmail API calls', async () => {
    const startTime = Date.now();
    await Promise.all([
      gmailAgent.listMessages(),
      gmailAgent.listMessages()
    ]);
    const duration = Date.now() - startTime;

    // Should take at least 1 second due to rate limiting
    expect(duration).toBeGreaterThan(1000);
  });
});

// src/agents/gmail/GmailAgent.ts (Red phase)
export class GmailAgent extends Agent {
  async scanPropertyEmails(timeframe: string) {
    throw new Error('Gmail scanning not implemented');
  }
}

// src/agents/gmail/GmailAgent.ts (Green phase)
export class GmailAgent extends Agent {
  private gmail: GmailAPI;

  constructor() {
    super();
    this.gmail = new GmailAPI({
      token: this.getValidToken()
    });
  }

  async scanPropertyEmails(timeframe: string) {
    const date = new Date();
    date.setHours(date.getHours() - 24); // 24 hours ago

    const query = `subject:(property OR house OR home) after:${date.toISOString().split('T')[0]}`;

    const response = await this.gmail.users.messages.list({
      userId: 'me',
      q: query,
      maxResults: 20
    });

    return Promise.all(
      response.data.messages.map(msg => this.getMessage(msg.id))
    );
  }
}
```

---

### **US-014: Lead Extraction & Qualification**
**As a** real estate agent
**I want** automatic lead processing
**So that** I can focus on high-quality prospects

**Description:**
Use GLM-4.5-Air to extract and qualify leads from incoming emails, identifying buyer preferences, budget, timeline, and likelihood of conversion for automatic CRM entry.

**Acceptance Criteria:**
- ✅ AI-powered lead extraction from email content
- ✅ Lead qualification scoring (hot/warm/cold)
- ✅ Contact information validation
- ✅ Duplicate lead detection
- ✅ Automatic CRM lead creation

**TDD Test-First Code Sample:**
```typescript
// tests/agents/lead-processing.test.ts
describe('Lead Processing', () => {
  test('should extract complete lead information', async () => {
    const emailContent = `
      Hi, I'm Sarah Johnson looking to buy a house.
      We have $425K budget for a 4-bedroom house.
      Available to look at properties this Saturday.
      Email me at sarahj@gmail.com, phone is (555) 123-4567
    `;

    const leadProcessor = new LeadProcessor();
    const lead = await leadProcessor.extractLead(emailContent);

    expect(lead.name).toBe('Sarah Johnson');
    expect(lead.email).toBe('sarahj@gmail.com');
    expect(lead.phone).toBe('(555) 123-4567');
    expect(lead.budget).toBe(425000);
    expect(lead.preferences.bedrooms).toBe(4);
    expect(lead.timeline).toMatch(/saturday/i);
  });

  test('should score lead quality accurately', async () => {
    const highQualityEmail = `
      First-time buyers, pre-qualified with $650K budget,
      looking in Scottsdale area, need closing by June 2025
    `;

    const score = await leadProcessor.scoreLeadQuality(highQualityEmail);

    expect(score).toBeGreaterThan(0.8);
    expect(score.intent).toBe('ready_buyer');
  });

  test('should detect and merge duplicate leads', async () => {
    const existingLead = {
      name: 'John Smith',
      email: 'john@email.com',
      created: '2025-09-01'
    };

    const duplicateEmail = `
      Hi, this is John again from john@email.com.
      Following up on our conversation about the property.
    `;

    const result = await leadProcessor.handlePotentialDuplicate(duplicateEmail);

    expect(result.isDuplicate).toBe(true);
    expect(result.mergeStrategy).toBe('UPDATE_EXISTING');
  });
});

// src/agents/lead-processing/LeadProcessor.ts (Red phase)
export class LeadProcessor {
  async extractLead(content: string) {
    throw new Error('Lead extraction not implemented');
  }
}

// src/agents/lead-processing/LeadProcessor.ts (Green phase)
export class LeadProcessor {
  private llm: GLMClient;

  async extractLead(content: string): Promise<Lead> {
    const prompt = `Extract lead information from this email. Return JSON:
    Email: "${content}"
    Format: {name, email, phone, budget, preferences: {bedrooms, location, type}}`;

    const response = await this.llm.generateJSONResponse(prompt);
    return this.validateAndNormalizeLead(response);
  }
}
```

---

#### **US-015: Response Generation & Email Drafting**
**As a** real estate agent
**I want** AI-generated email responses
**So that** I can respond quickly while maintaining professionalism

**Description:**
Generate contextually appropriate email responses using GLM-4.5-Air trained on real estate communication patterns, including property follow-ups, showing confirmations, and offer negotiations.

**Acceptance Criteria:**
- ✅ Personalized response generation
- ✅ Real estate terminology accuracy
- ✅ Multiple response tone options
- ✅ Property-specific content inclusion
- ✅ Agent brand voice consistency

**TDD Test-First Code Sample:**
```typescript
// tests/agents/email-responses.test.ts
describe('Email Response Generation', () => {
  test('should generate personalized property inquiry responses', async () => {
    const context = {
      agentName: 'Sarah Martinez',
      agentPhone: '(555) 987-6543',
      property: {
        address: '123 Oak Street',
        price: 450000,
        bedrooms: 3,
        bathrooms: 2
      },
      inquiryType: 'showing_request'
    };

    const responseGenerator = new EmailResponseGenerator();
    const email = await responseGenerator.generateResponse(context);

    expect(email.subject).toMatch(/showing|tour|viewing/i);
    expect(email.body).toContain('Sarah Martinez');
    expect(email.body).toContain('123 Oak Street');
    expect(email.body).toContain('(555) 987-6543');
    expect(email.body.length).toBeGreaterThan(200);
  });

  test('should adapt tone based on lead qualification', () => {
    const highPriorityLead = { score: 0.9, urgency: 'pre-qualified_buyer' };
    const lowPriorityLead = { score: 0.3, urgency: 'just_looking' };

    const professional = generator.adaptTone(highPriorityLead);
    const casual = generator.adaptTone(lowPriorityLead);

    expect(professional).toContain('pleasure');
    expect(casual).toContain('happy');
  });

  test('should include proper real estate disclaimers', async () => {
    const email = await generator.generateOfferResponse({
      offerAmount: 445000,
      propertyPrice: 450000
    });

    expect(email.body).toMatch(/not intended as legal advice/i);
    expect(email.body).toContain('consult attorney');
  });
});

// src/agents/email/EmailResponseGenerator.ts
export class EmailResponseGenerator {
  private llm: GLMClient;

  async generateResponse(context: ResponseContext): Promise<Email> {
    const prompt = `Generate a professional real estate email response:

    Context: ${JSON.stringify(context)}
    Agent: ${context.agentName} specializing in ${context.property.location}

    Requirements:
    - Personalized greeting using buyer name
    - Highlight relevant property features
    - Include next action steps
    - Professional closing with contact info
    - Keep under 300 words

    Return JSON: {subject, body}`;

    const response = await this.llm.generateJSONResponse(prompt);
    return this.addAgentSignature(response);
  }
}
```

---

### **US-016: Automated Email Campaigns**
**As a** real estate agent
**I want** automated follow-up sequences
**So that** I can nurture leads consistently

**Description:**
Create automated email workflows for lead nurturing, showing follow-ups, offer responses, and closing assistance using scheduled email sequences through GLM-4.5-Air content generation.

**Acceptance Criteria:**
- ✅ Configurable email sequences
- ✅ Lead-based content personalization
- ✅ Timing and frequency optimization
- ✅ Open rate and engagement tracking
- ✅ Manual override capabilities

**TDD Test-First Code Sample:**
```typescript
// tests/agents/email-campaigns.test.ts
describe('Email Campaign Automation', () => {
  test('should execute lead nurturing sequences', async () => {
    const campaign = new EmailCampaignManager();

    await campaign.startLeadNurture({
      leadId: 'john_doe_123',
      leadEmail: 'john@email.com',
      leadScore: 0.7,
      propertyInterest: '123 Oak Street'
    });

    const emailsSent = await campaign.getEmailHistory('john_doe_123');

    expect(emailsSent).toHaveLength(1); // Welcome email sent
    expect(emailsSent[0].subject).toContain('Getting Started');
  });

  test('should personalize content based on lead data', async () => {
    const campaign = new EmailCampaignManager();

    const lead = {
      id: 'sarah_456',
      name: 'Sarah',
      budget: 500000,
      preferences: {
        location: 'downtown',
        bedrooms: 3,
        style: 'modern'
      }
    };

    const content = await campaign.generatePersonalizedContent(lead);

    expect(content.subject).toBeDefined();
    expect(content.body).toContain('downtown');
    expect(content.body).toContain('3 bedroom');
    expect(content.body).toContain('Sarah');
  });

  test('should schedule follow-up emails strategically', async () => {
    const scheduler = new EmailScheduler();

    const sequence = [
      { daysAfter: 1, type: 'welcome' },
      { daysAfter: 3, type: 'property_tour' },
      { daysAfter: 7, type: 'market_update' }
    ];

    const schedule = await scheduler.createSchedule(sequence);

    expect(schedule.upcoming.length).toBeGreaterThan(0);
    expect(schedule.upcoming[0].scheduledDate).toBeGreaterThan(Date.now());
  });

  test('should handle email bounces and unsubscribes', async () => {
    const monitor = new EmailMonitor();

    // Mock bounce event
    await monitor.handleEmailEvent({
      type: 'bounce',
      email: 'invalid@email.com',
      leadId: 'lead_123'
    });

    const lead = await monitor.getLeadStatus('lead_123');
    expect(lead.emailStatus).toBe('bounced');
    expect(lead.communicationEnabled).toBe(false);
  });
});

// src/agents/email/EmailCampaignManager.ts
export class EmailCampaignManager {
  private llm: GLMClient;
  private scheduler: EmailScheduler;

  async startLeadNurture(lead: Lead) {
    // Generate personalized email sequences
    const sequence = await this.llm.generateEmailSequence(lead);

    // Schedule emails using calendar agent
    await this.scheduler.scheduleCampaign(sequence, lead);

    // Log campaign start in CRM
    await this.crmAgent.logCampaignStart(lead.id, sequence.type);
  }
}
```

---

## **Epic 4: CRM Agent (Week 4-5)**

### **US-017: Google Sheets CRM Integration**
**As a** real estate agent
**I want** my CRM data accessible to OrcaAI
**So that** I can manage leads through natural conversation

**Description:**
Connect to Google Sheets as a lightweight CRM platform, enabling OrcaAI to read/write lead information, track deal pipeline, and manage contact databases through the Sheets API.

**Acceptance Criteria:**
- ✅ Google Sheets API authentication
- ✅ Lead worksheet operations (CRUD)
- ✅ Property tracking sheets
- ✅ Deal pipeline management
- ✅ Backup and sync capabilities

---

### **US-018: Automated Lead Management**
**As a** real estate agent
**I want** intelligent lead progression
**So that** I can focus on high-priority prospects

**Description:**
Use GLM-4.5-Air to analyze lead data and suggest next actions, implementing workflow automation for lead scoring, pipeline movement, and follow-up task generation.

**Acceptance Criteria:**
- ✅ Lead scoring algorithm integration
- ✅ Automated pipeline progression
- ✅ Intelligent next-action suggestions
- ✅ Lead activity tracking
- ✅ Conversion funnel analytics

---

### **US-019: CRM Intelligence Dashboard**
**As a** real estate agent
**I want** insights into my business metrics
**So that** I can make data-driven decisions

**Description:**
Build real-time CRM analytics that track lead sources, conversion rates, deal velocity, and performance metrics using Google Sheets formulas and OrcaAI-generated insights.

**Acceptance Criteria:**
- ✅ Real-time pipeline visualization
- ✅ Lead source attribution
- ✅ Performance metrics calculation
- ✅ Automated reporting generation
- ✅ Predictive analytics recommendations

---

### **US-020: CRM Synchronization Engine**
**As a** real estate agent
**I want** consistent data across platforms
**So that** I can avoid duplicate work

**Description:**
Implement bidirectional synchronization between multiple data sources, ensuring lead information stays consistent across Gmail, Google Calendar, Drive, and external MLS systems.

**Acceptance Criteria:**
- ✅ Bidirectional data synchronization
- ✅ Conflict resolution algorithms
- ✅ Data validation and cleanup
- ✅ Change tracking and audit logs
- ✅ Offline synchronization capability

---

## **Epic 5: Calendar Agent (Weeks 5-6)**

### **US-021: Calendar Access & Availability**
**As a** real estate agent
**I want** OrcaAI to check my calendar
**So that** I can coordinate showings efficiently

**Description:**
Integrate with Google Calendar API to read availability patterns, detect conflicts, and find optimal times for property showings and appointment scheduling.

**Acceptance Criteria:**
- ✅ Real-time calendar availability checking
- ✅ Automatic conflict detection
- ✅ Time zone consideration
- ✅ Recurring appointment patterns
- ✅ Travel time calculations

---

### **US-022: Automated Scheduling Workflows**
**As a** real estate agent
**I want** hands-free appointment booking
**So that** I can focus on client interactions

**Description:**
Build intelligent scheduling algorithms that coordinate multiple parties, optimize time slots, and automatically send invites with property information and meeting details.

**Acceptance Criteria:**
- ✅ Multi-party availability matching
- ✅ Automatic invitation generation
- ✅ Property packet inclusion
- ✅ Reminder system integration
- ✅ Cancellations and rescheduling

---

### **US-023: Appointment Management**
**As a** real estate agent
**I want** comprehensive appointment tracking
**So that** I can stay organized

**Description:**
Create appointment lifecycle management including preparation checklists, client communication sequences, and post-appointment follow-up automation.

**Acceptance Criteria:**
- ✅ Pre-appointment preparation tracking
- ✅ Client communications management
- ✅ Appointment outcome logging
- ✅ Follow-up sequence automation
- ✅ Performance metrics collection

---

### **US-024: Calendar Intelligence**
**As a** real estate agent
**I want** insights into my scheduling patterns
**So that** I can optimize my business

**Description:**
Analyze calendar data to provide business intelligence about productive periods, client preferences, deal progression rates, and scheduling optimization recommendations.

**Acceptance Criteria:**
- ✅ Productivity pattern analysis
- ✅ Peak performance identification
- ✅ Client preference learning
- ✅ Scheduling recommendations
- ✅ Revenue correlation tracking

---

## **Epic 6: Drive Agent (Weeks 6-7)**

### **US-025: Document Organization System**
**As a** real estate agent
**I want** automated document management
**So that** I can keep files organized

**Description:**
Implement intelligent document storage with automatic folder creation, naming conventions, and tagging systems for property documents, contracts, and client communications.

**Acceptance Criteria:**
- ✅ Automatic folder hierarchy creation
- ✅ File naming standardization
- ✅ Document tagging and metadata
- ✅ Version control system
- ✅ Document search and retrieval

---

### **US-026: Property Packet Generation**
**As a** real estate agent
**I want** instant property presentations
**So that** I can prepare quickly

**Description:**
Build automated property packet generation that pulls MLS data, creates branded documents, and compiles comprehensive showing packages in minutes using GLM-4.5-Air.

**Acceptance Criteria:**
- ✅ MLS data integration
- ✅ Branded document templates
- ✅ Comprehensive property packages
- ✅ Client customization
- ✅ Multi-format exports

---

### **US-027: Client Document Sharing**
**As a** real estate agent
**I want** secure document sharing
**So that** I can collaborate safely

**Description:**
Implement secure document sharing with access controls, tracking, and automated notification systems for client disclosures, contracts, and offering documents.

**Acceptance Criteria:**
- ✅ Permission-based access control
- ✅ Usage tracking and reporting
- ✅ Expiration and renewal systems
- ✅ Client notification automation
- ✅ Digital signature integration

---

### **US-028: Document Intelligence**
**As a** real estate agent
**I want** smart document processing
**So that** I can extract insights automatically

**Description:**
Add AI-powered document processing capabilities including contract analysis, offer evaluation, financial document processing, and automated data extraction.

**Acceptance Criteria:**
- ✅ Contract analysis and summary
- ✅ Financial document processing
- ✅ Key information extraction
- ✅ Automated form filling
- ✅ Risk assessment recommendations

---

## **📊 Project Metrics**

### **TDD Quality Metrics**
- **Test Coverage:** >90% for all user stories
- **Test Passing Rate:** >95% throughout development
- **Refactoring Cycles:** Red-Green-Refactor completion for each story
- **Integration Test Success:** >98% for cross-agent workflows

### **Development Velocity**
- **Stories per Week:** 7 user stories completed
- **Sprint Efficiency:** >85% of estimated work completed
- **Defect Rate:** <5% production defects
- **Code Quality:** SonarQube rating A+ throughout

### **Real Estate Business Metrics**
- **Query Response Time:** <500ms AI intent analysis
- **Schedule Success Rate:** >98% conflict-free bookings
- **Lead Extraction Accuracy:** >92% information accuracy
- **Email Campaign Engagement:** >60% open rates

---

## **🧪 TDD Implementation Strategy**

### **Three-Phase Workflow per User Story**

#### **Phase 1: Red (Failing Tests)**
```typescript
// Write tests first - expect failure
test('should analyze user intent', () => {
  const analyzer = new IntentAnalyzer();
  expect(analyzer.analyze('schedule showing')).toEqual({
    intent: 'schedule_showing',
    confidence: 0.95
  });
}); // ❌ Fails - implementation doesn't exist
```

#### **Phase 2: Green (Minimal Implementation)**
```typescript
// Implement bare minimum to pass tests
class IntentAnalyzer {
  analyze(query: string) {
    // Hardcoded for test passing
    return { intent: 'schedule_showing', confidence: 0.95 };
  }
} // ✅ Tests now pass
```

#### **Phase 3: Refactor (Production Quality)**
```typescript
// Enhance with production features
class IntentAnalyzer {
  private llm: GLMClient;

  async analyze(query: string) {
    const prompt = `Analyze real estate intent: ${query}`;
    const response = await this.llm.analyzeIntent(prompt);

    return {
      intent: response.intent,
      confidence: response.confidence,
      entities: this.extractEntities(response),
      timestamp: Date.now()
    };
  }
} // ✅ Production quality with additional features
```

### **Integration Testing Strategy**
```typescript
// Cross-agent workflow testing
describe('End-to-End Workflows', () => {
  test('complete lead intake workflow', async () => {
    // Email received
    await gmailAgent.receiveEmail(mockPropertyInquiry);

    // GLM analysis
    const intent = await orchestrator.handleMessage(emailContent);

    // Multi-agent execution
    await orchestrator.handleMessage(intent);

    // Verify results across all agents
    expect(crmAgent.getLead(emailLeadId)).toBeDefined();
    expect(calendarAgent.hasAppointment(eventId)).toBe(true);
    expect(gmailAgent.sentConfirmation(email)).toBe(true);
  });
});
```

---

## **🚀 Deployment & Launch Strategy**

### **Week 13: Beta Deployment**
- Target 50 pre-qualified real estate agents
- Full functional testing in production environment
- 24/7 monitoring and support

### **Week 14-16: General Launch**
- Scaling to 1000 agents
- Marketing campaign launch
- Support team expansion

### **Success Metrics**
- **Month 3:** 500 active agents, >95% user satisfaction
- **Month 6:** 2000 active agents, 80% operational efficiency improvement
- **Year 1:** Market leadership, >5000 agents, $500K monthly revenue

---

**Ready for TDD implementation!** 🏗️

*OrcaAI Project Plan*
*TDD-Driven Development*  
*Test-First Implementation*
