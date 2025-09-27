# 🏠 ORCA - Open WebUI + Cloudflare Agents Real Estate AI

## **Product Requirements Document**

### **Version:** 1.0.0
### **Date:** September 26, 2025
### **Authors:** Cline AI Assistant

---

## **📋 Executive Summary**

ORCA (ORchestration Real estate AI) is an intelligent agentic assistant specifically designed for real estate professionals, built using Open WebUI as the frontend and Cloudflare Agents SDK as the orchestration backend. This system automates the complete real estate agent workflow through conversational AI, enabling agents to conduct their entire business through a chat interface.

### **Core Capabilities**
- **Intelligent Orchestration:** Coordinated AI agents managing emails, CRM, calendar, and documents
- **Conversational Workflows:** Natural language commands for business automation
- **Google Workspace Integration:** Seamless connection to Gmail, Sheets (CRM), Calendar, and Drive
- **Global Performance:** Cloudflare edge deployment for worldwide accessibility
- **Size Optimized:** 95% reduction from original 6.5GB codebase to < 400MB

---

## **🎯 Business Case & Problem Statement**

### **Current Pain Points for Real Estate Agents**
- **Manual email sorting:** Hours spent sorting property inquiries from spam
- **CRM data entry:** Tedious manual input of lead information
- **Scheduling complexity:** Coordinating showings across multiple parties and calendars
- **Document management:** Lost time tracking property documents and MLS listings
- **Multi-system fatigue:** Switching between email, CRM, calendar, and drive daily

### **Solution Benefits**
- **80% time savings** on administrative tasks
- **Zero missed leads** with automated email monitoring
- **Error-free scheduling** with AI-coordinated calendars
- **Unified interface** - conduct entire business through chat
- **Real-time collaboration** with shared agent interfaces

---

## **🏗️ Technical Architecture**

### **Core Technology Stack**

| **Component** | **Technology** | **Purpose** |
|---|---|---|
| **Frontend UI** | Open WebUI (SvelteKit) | Rich, streaming chat interface |
| **Backend Orchestration** | Cloudflare Agents SDK | Persistent AI agents with durable objects |
| **AI Model** | GLM-4.5-Air via Open Router | Intent analysis and response generation |
| **Deployment** | Cloudflare Pages/Workers | Global edge network delivery |
| **Integrations** | Google Workspace APIs | Email, CRM, Calendar, Document management |

### **System Architecture**
```
┌─────────────────┐    ┌────────────────────┐
│   Open WebUI    │────│  Cloudflare Agents │
│   (SvelteKit)   │    │ (Durable Objects)  │
└─────────────────┘    └────────────────────┘
        │                     │
        │   WebRTC+HTTP       │
        │   (Streaming)       │
        └─────────┬───────────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Gmail   │ │ Sheets  │ │Calendar │ │ Drive   │
│ Agent   │ │(CRM)    │ │ Agent   │ │ Agent   │
│         │ │ Agent   │ │         │ │         │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
      │         │          │          │
      └─────────┼──────────┼──────────┘
                │
       ┌────────▼────────┐
       │  Google Workspace  │
       │     APIs         │
       └─────────────────┘
```

---

## **🤖 AI Agent Architecture**

### **1. Orchestration Agent (Main Controller)**

```typescript
export class OrcaOrchestrationAgent extends Agent {
  private llm: OrcaLLMClient;
  private gmailAgent: GmailAgent;
  private crmAgent: CRMSheetsAgent;
  private calendarAgent: CalendarAgent;
  private driveAgent: DriveAgent;

  async handleMessage(message: string, userId: string) {
    // Step 1: Intent Analysis via GLM-4.5-Air
    const analysis = await this.analyzeIntent(message);

    // Step 2: Route to specialized agents
    switch (analysis.intent) {
      case 'email_check':
        return await this.processEmailWorkflow(message, analysis);
      case 'schedule_showing':
        return await this.processSchedulingWorkflow(message, analysis);
      case 'crm_update':
        return await this.processCRMWorkflow(message, analysis);
      default:
        return await this.generateGeneralResponse(message);
    }
  }

  private async analyzeIntent(message: string) {
    return await this.llm.generate({
      model: 'z-ai/glm-4.5-air:free',
      messages: [{
        role: 'system',
        content: 'Analyze real estate intent. Return JSON: {"intent": "...", "entities": {...}}'
      }, {
        role: 'user',
        content: message
      }],
      temperature: 0.1
    });
  }
}
```

### **2. Gmail Agent - Email Management**

```typescript
export class GmailAgent extends Agent {
  private gmailApi: GoogleAPIs;

  async checkPropertyInquiries(userId: string) {
    const query = await this.llm.generateGmailSearchQuery(
      'property inquiries from past week'
    );

    const messages = await this.gmailApi.listMessages({
      userId,
      q: query,
      maxResults: 50
    });

    // Process each email with AI
    for (const message of messages) {
      const analysis = await this.llm.extractLeadInfo(
        await this.gmailApi.getMessageContent(message.id)
      );

      if (analysis.isPropertyInquiry) {
        await this.crmAgent.addLead(analysis.leadInfo);
      }
    }

    return `${messages.length} property inquiries processed`;
  }

  async sendFollowUpEmail(email: FollowUpEmail) {
    const draft = await this.llm.generateEmailResponse({
      template: 'follow_up',
      context: email.leadInfo,
      tone: 'professional'
    });

    return await this.gmailApi.sendMessage({
      to: email.to,
      subject: draft.subject,
      body: draft.body
    });
  }
}
```

### **3. CRM Agent - Lead Management**

```typescript
export class CRMSheetsAgent extends Agent {
  private sheetsApi: GoogleAPIs;

  async addLead(leadData: LeadInfo) {
    await this.sheetsApi.appendValues({
      spreadsheetId: env.CRM_SHEET_ID,
      range: 'Leads!A:J',
      values: [[
        leadData.name,
        leadData.email,
        leadData.phone,
        leadData.budget,
        leadData.propertyType,
        leadData.location,
        'NEW_LEAD',
        new Date().toISOString()
      ]]
    });

    // Create property-specific follow-up tasks
    await this.createFollowUpWorkflow(leadData);

    return `Lead added to CRM: ${leadData.name}`;
  }

  async updateLeadStatus(leadId: string, status: string, notes?: string) {
    const leadRow = await this.findLeadById(leadId);
    await this.sheetsApi.updateRange({
      spreadsheetId: env.CRM_SHEET_ID,
      range: `Leads!G${leadRow}`,
      value: status
    });

    if (notes) {
      await this.sheetsApi.updateRange({
        spreadsheetId: env.CRM_SHEET_ID,
        range: `Leads!K${leadRow}`,
        value: notes
      });
    }
  }
}
```

### **4. Calendar Agent - Scheduling**

```typescript
export class CalendarAgent extends Agent {
  private calendarApi: GoogleAPIs;

  async schedulePropertyShowing(leadData: LeadInfo, propertyAddress: string) {
    // Step 1: Check agent availability
    const availability = await this.checkAvailability();

    if (!availability.hasOpenSlot) {
      return {
        success: false,
        message: 'No availability within next week',
        alternatives: availability.suggestions
      };
    }

    // Step 2: Create calendar event
    const event = await this.calendarApi.events.insert({
      calendarId: 'primary',
      resource: {
        summary: `Property Showing: ${propertyAddress}`,
        description: `Client: ${leadData.name}\nPhone: ${leadData.phone}`,
        location: propertyAddress,
        start: { dateTime: availability.selectedSlot.start },
        end: { dateTime: availability.selectedSlot.end },
        attendees: [
          { email: leadData.email, displayName: leadData.name },
          { email: env.AGENT_EMAIL },
          { email: env.SELLER_AGENT_EMAIL, displayName: 'Seller Agent' }
        ],
        reminders: {
          useDefault: true,
          overrides: [
            { method: 'email', minutes: 24 * 60 },
            { method: 'popup', minutes: 30 }
          ]
        }
      }
    });

    // Step 3: Update CRM and Drive
    await this.crmAgent.logSchedulingActivity(leadData.id, event.id);
    await this.driveAgent.createShowingChecklist(propertyAddress, leadData.name);

    return {
      success: true,
      eventId: event.id,
      calendarLink: event.htmlLink,
      message: 'Showing scheduled successfully'
    };
  }
}
```

### **5. Drive Agent - Document Management**

```typescript
export class DriveAgent extends Agent {
  private driveApi: GoogleAPIs;

  async createLeadDocumentFolder(leadData: LeadInfo, propertyAddress: string) {
    // Create main folder
    const leadFolder = await this.driveApi.files.create({
      name: `${leadData.name} - ${propertyAddress}`,
      mimeType: 'application/vnd.google-apps.folder',
      parents: [env.BASE_PROPERTY_FOLDER_ID]
    });

    // Generate property info sheet
    const propertyInfo = await this.generatePropertyInfoDoc({
      propertyAddress,
      leadName: leadData.name,
      budget: leadData.budget,
      timeline: leadData.timeline
    });

    // Create subfolders
    const subfolders = await Promise.all([
      this.createSubFolder('MLS Documents', leadFolder.id),
      this.createSubFolder('Client Communications', leadFolder.id),
      this.createSubFolder('Financial Documents', leadFolder.id),
      this.createSubFolder('Legal Documents', leadFolder.id)
    ]);

    // Share with lead if they opt-in
    if (leadData.sharingOptIn) {
      await this.shareFolderWithClient(
        leadFolder.id,
        leadData.email,
        `${propertyAddress} - Property Documents`
      );
    }

    return {
      folderId: leadFolder.id,
      subfolders,
      propertyDocId: propertyInfo.id
    };
  }

  async shareFolderWithClient(folderId: string, clientEmail: string, message: string) {
    const permission = {
      type: 'user',
      role: 'reader',
      emailAddress: clientEmail
    };

    await this.driveApi.permissions.create({
      fileId: folderId,
      resource: permission,
      emailMessage: message,
      sendNotificationEmail: true
    });
  }
}
```

---

## **📱 Frontend Integration**

### **Open WebUI Chat Enhancements**

#### **Smart Action Suggestions**
```svelte
<!-- src/lib/components/chat/ActionSuggestions.svelte -->
<script>
  export let userMessage;

  $: suggestions = generateSmartSuggestions(userMessage);

  function generateSmartSuggestions(message) {
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes('check') && lowerMessage.includes('email')) {
      return [
        {
          icon: 'email',
          label: 'Check property inquiries',
          action: () => orcaAgent.checkEmailInquiries()
        },
        {
          icon: 'lead',
          label: 'Review new leads',
          action: () => orcaAgent.reviewRecentLeads()
        }
      ];
    }

    if (lowerMessage.includes('schedule') || lowerMessage.includes('showing')) {
      return [
        {
          icon: 'calendar',
          label: 'Check my availability',
          action: () => calendarAgent.checkAvailability()
        },
        {
          icon: 'property',
          label: 'Find listing details',
          action: () => orcaAgent.searchMLS()
        }
      ];
    }

    return [];
  }
</script>

{#each suggestions as suggestion}
  <button
    class="action-chip"
    on:click={suggestion.action}
    class:heet={suggestion.type === 'email'}
  >
    <Icon name={suggestion.icon} size="small" />
    {suggestion.label}
  </button>
{/each}
```

#### **Real-Time Agent Status Dashboard**

```svelte
<!-- src/lib/components/dashboard/AgentStatus.svelte -->
<script>
  export let agentType;

  $: status = $agentStatuses[agentType];

  // Real-time status via WebSocket
  const statusColors = {
    idle: 'gray',
    active: 'blue',
    processing: 'yellow',
    complete: 'green',
    error: 'red'
  };
</script>

<div class="agent-status-card" class:status--{statusColors[status.state]}>
  <div class="agent-icon">
    <Icon name={getAgentIcon(agentType)} />
  </div>

  <div class="agent-info">
    <h4>{formatAgentName(agentType)}</h4>
    <span class="status-text">{status.message}</span>

    {#if status.progress}
      <div class="progress-bar">
        <div
          class="progress-fill"
          style="width: {status.progress.percentage}%"
        ></div>
      </div>
    {/if}
  </div>

  {#if status.isActive}
    <div class="loading-spinner">
      <Spinner size="small" />
    </div>
  {/if}
</div>

<style>
  .agent-status-card {
    display: flex;
    align-items: center;
    padding: 12px;
    border-radius: 8px;
    border: 2px solid var(--color-gray-200);
    transition: border-color 0.3s ease;
  }

  .agent-status-card.status--blue { border-color: var(--color-blue-500); }
  .agent-status-card.status--yellow { border-color: var(--color-yellow-500); }
  .agent-status-card.status--green { border-color: var(--color-green-500); }
  .agent-status-card.status--red { border-color: var(--color-red-500); }

  .progress-bar {
    width: 100%;
    height: 4px;
    background: var(--color-gray-200);
    border-radius: 2px;
    margin-top: 8px;
  }

  .progress-fill {
    height: 100%;
    background: var(--color-blue-500);
    border-radius: 2px;
    transition: width 0.3s ease;
  }
</style>
```

#### **Property Document Viewer**

```svelte
<!-- src/lib/components/chat/PropertyDocsViewer.svelte -->
<script>
  export let leadId;
  export let propertyAddress;

  let documents = [];
  let selectedDoc = null;

  onMount(async () => {
    documents = await driveAgent.getPropertyDocuments(leadId, propertyAddress);
  });

  function openDocument(docId) {
    // Open in new tab for native Google Docs experience
    window.open(`https://docs.google.com/document/d/${docId}/edit`, '_blank');
  }

  function shareWithClient(docId, clientEmail) {
    // Share document with client
    driveAgent.shareDocument(docId, clientEmail);
  }
</script>

<div class="property-docs">
  <h3>Property Documents: {propertyAddress}</h3>

  <div class="doc-list">
    {#each documents as doc}
      <div class="doc-item" on:click={() => openDocument(doc.id)}>
        <div class="doc-icon">
          <Icon name={getDocIcon(doc.type)} />
        </div>

        <div class="doc-info">
          <h4>{doc.name}</h4>
          <span class="doc-modified">Modified {formatDate(doc.modifiedTime)}</span>
        </div>

        <div class="doc-actions">
          {#if doc.canBeShared}
            <button
              class="share-btn"
              on:click|stopPropagation={() => shareWithClient(doc.id, leadData.email)}
            >
              Share with Client
            </button>
          {/if}
        </div>
      </div>
    {/each}
  </div>
</div>
```

---

## **🔧 Google Workspace API Configuration**

### **Authentication Setup**

```typescript
// src/lib/auth/googleOAuth.ts
export class GoogleOAuthManager {
  private clientId = env.GOOGLE_CLIENT_ID;
  private clientSecret = env.GOOGLE_CLIENT_SECRET;

  async getValidToken(scopes: string[]): Promise<string> {
    const tokens = await this.getStoredTokens();

    if (this.isExpired(tokens)) {
      return await this.refreshToken(tokens.refreshToken);
    }

    return tokens.accessToken;
  }

  async initiateOAuthFlow(scopes: string[]): Promise<string> {
    const authUrl = `https://accounts.google.com/o/oauth2/auth?` +
      new URLSearchParams({
        client_id: this.clientId,
        redirect_uri: env.GOOGLE_REDIRECT_URI,
        scope: scopes.join(' '),
        response_type: 'code',
        access_type: 'offline',
        prompt: 'consent'
      });

    return authUrl;
  }
}
```

### **API Client Configuration**

```typescript
// src/lib/apis/google/index.ts
export const googleAPIs = {
  gmail: new GmailAPIManager(),
  sheets: new SheetsAPIManager(),
  calendar: new CalendarAPIManager(),
  drive: new DriveAPIManager()
};

class GmailAPIManager {
  async listMessages(query: string) {
    const token = await googleOAuth.getValidToken([
      'https://www.googleapis.com/auth/gmail.readonly',
      'https://www.googleapis.com/auth/gmail.send'
    ]);

    return fetch(`https://gmail.googleapis.com/gmail/v1/users/me/messages?q=${encodeURIComponent(query)}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
  }
}

class SheetsAPIManager {
  async appendValues(spreadsheetId: string, range: string, values: any[][]) {
    const token = await googleOAuth.getValidToken([
      'https://www.googleapis.com/auth/spreadsheets'
    ]);

    return fetch(`https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/${range}:append?valueInputOption=RAW`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ values })
    });
  }
}

class CalendarAPIManager {
  async createEvent(eventData: GoogleCalendarEvent) {
    const token = await googleOAuth.getValidToken([
      'https://www.googleapis.com/auth/calendar.events'
    ]);

    return fetch('https://www.googleapis.com/calendar/v3/calendars/primary/events', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(eventData)
    });
  }
}

class DriveAPIManager {
  async createFolder(name: string, parentId?: string) {
    const token = await googleOAuth.getValidToken([
      'https://www.googleapis.com/auth/drive.file'
    ]);

    const requestBody = {
      name,
      mimeType: 'application/vnd.google-apps.folder',
      ...(parentId && { parents: [parentId] })
    };

    return fetch('https://www.googleapis.com/drive/v3/files', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    });
  }
}
```

---

## **💽 Code Size Optimization Strategies**

### **1. Backend Size Reduction: 95% Target**

| **Component** | **Heavy Approach** | **Optimized Approach** | **Reduction** |
|---|---|---|---|
| **AI Processing** | 2.4GB Python venv | 5MB Cloudflare Agents | 99.8% |
| **Database** | SQLAlchemy ORMs | Google Workspace APIs | 99.7% |
| **Web Framework** | FastAPI server | Serverless Vercel SDK calls | 99.9% |
| **ML Libraries** | PyTorch/ONNX | GLM-4.5-Air API calls | ~100% |

### **2. Frontend Optimization: Core + Lazy Loading**

#### **Bundle Splitting Strategy**
- **Core Chat:** 15MB (always loaded)
- **Gmail Agent UI:** 8MB (loaded on email commands)
- **CRM Interface:** 6MB (loaded when accessing leads)
- **Calendar Tools:** 5MB (loaded for scheduling)
- **Document Viewer:** 7MB (loaded when viewing docs)

#### **Implementation Pattern**
```typescript
// src/lib/agents/index.ts
export const agentComponents = {
