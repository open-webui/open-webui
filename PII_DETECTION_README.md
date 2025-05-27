# PII Detection Feature

This feature adds automatic detection and masking of Personally Identifiable Information (PII) in chat messages using the NENNA.ai API.

## Features

- **Real-time PII Detection**: Detects PII in user input with debounced API calls (500ms delay)
- **Visual Highlighting**: Highlights detected PII entities in the input field with color-coded highlighting
- **Automatic Masking**: Masks PII before sending to AI models
- **Response Unmasking**: Automatically unmasks PII in AI responses
- **Session Management**: Uses NENNA API sessions for consistent masking/unmasking

## Supported PII Types

The system detects and highlights the following PII types:

- Names (PERSON)
- Email addresses (EMAIL)
- Phone numbers (PHONE_NUMBER/PHONENUMBER)
- Addresses (ADDRESS)
- Social Security Numbers (SSN)
- Credit card numbers (CREDIT_CARD)
- Dates and times (DATE_TIME)
- IP addresses (IP_ADDRESS)
- URLs (URL)
- IBAN numbers (IBAN)
- Medical licenses (MEDICAL_LICENSE)
- US Passports (US_PASSPORT)
- US Driver's licenses (US_DRIVER_LICENSE)

## Setup

1. **Get NENNA API Key**: Sign up at [nenna.ai](https://nenna.ai) to get your API key
2. **Configure Settings**: Go to Settings > PII Detection and:
   - Enable PII Detection
   - Enter your NENNA API key
   - Test the connection

## How It Works

### Input Processing

1. User types in the message input field
2. After 500ms of inactivity, the text is sent to NENNA API for PII detection
3. Detected PII entities are highlighted in the input with different colors per type
4. When submitting, the masked version is sent to the AI model

### Response Processing

1. AI model receives and processes the masked text
2. AI response is automatically unmasked using the session context
3. User sees the original unmasked response

### Session Management

- A NENNA session is created when PII detection is enabled
- Sessions maintain consistent entity mappings for masking/unmasking
- Sessions automatically expire after 24 hours

## Files Modified

### Core API

- `src/lib/apis/pii/index.ts` - NENNA API integration
- `src/lib/utils/pii.ts` - Utility functions and session management

### UI Components

- `src/lib/components/common/RichTextInput.svelte` - Added PII detection to text input
- `src/lib/components/common/RichTextInput/PiiHighlighter.ts` - TipTap extension for highlighting
- `src/lib/components/chat/MessageInput.svelte` - Integrated PII detection in message input
- `src/lib/components/chat/Messages/ResponseMessage.svelte` - Added response unmasking
- `src/lib/components/chat/Settings/PiiSettings.svelte` - Settings configuration UI

## Configuration

The PII detection feature can be configured through the settings:

```typescript
{
  piiDetection: {
    enabled: boolean,
    apiKey: string
  }
}
```

## Color Coding

Each PII type has a distinct color for easy identification:

- **PERSON**: Red (#ff6b6b)
- **EMAIL**: Teal (#4ecdc4)
- **PHONE_NUMBER**: Blue (#45b7d1)
- **ADDRESS**: Green (#96ceb4)
- **SSN**: Yellow (#feca57)
- **CREDIT_CARD**: Pink (#ff9ff3)
- And more...

## Privacy & Security

- PII data is processed by NENNA.ai's secure API
- Sessions are temporary and expire automatically
- Masked data is sent to AI models, not original PII
- API keys are stored locally in browser settings

## Troubleshooting

### Connection Issues

- Verify your NENNA API key is correct
- Check network connectivity
- Ensure NENNA API is accessible

### Highlighting Not Working

- Check if PII detection is enabled in settings
- Verify API key is configured
- Check browser console for errors

### Masking/Unmasking Issues

- Ensure a valid session exists
- Check if session has expired (24h default)
- Verify API key permissions
