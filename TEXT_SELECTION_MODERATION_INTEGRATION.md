# Text Selection + Moderation Integration Guide

## ✅ What's Been Connected

### Backend (`backend/open_webui/utils/moderation.py`)
1. **Fixed OpenAI API calls** - Changed from incorrect `responses.create()` to correct `chat.completions.create()`
2. **Integrated highlighted texts** - When parents select concerning text, it's now included in the moderation prompt
3. **Two modes supported**:
   - **Generation Mode**: Create a response from scratch with moderation rules
   - **Refactoring Mode**: Take an existing response and refactor it based on rules + highlighted texts

### Frontend API (`src/lib/apis/moderation/index.ts`)
1. **Added parameters**:
   - `originalResponse` - The AI's original response to refactor
   - `highlightedTexts` - Array of text strings the parent selected/flagged
2. **Updated interfaces** to include these new fields

### How It Works

```typescript
// Parents can now:
1. View a chat conversation
2. Select/highlight problematic text in messages (already implemented in UserMessage.svelte)
3. Those selections are saved via selectionSyncService
4. Apply moderation strategies with those selections to refactor the response
```

## 🎯 How to Use in Parent Dashboard

### Example: Retrieve selections and apply moderation

```typescript
import { savedSelections } from '$lib/stores';
import { applyModeration } from '$lib/apis/moderation';
import { get } from 'svelte/store';

async function refactorWithSelections(
    chatId: string,
    messageId: string,
    childPrompt: string,
    originalResponse: string
) {
    // 1. Get saved selections for this specific message
    const allSelections = get(savedSelections);
    const messageSelections = allSelections.filter(
        sel => sel.chatId === chatId && 
               sel.messageId === messageId &&
               sel.role === 'assistant'  // or 'user' depending on which message
    );
    
    // 2. Extract just the text strings
    const highlightedTexts = messageSelections.map(sel => sel.text);
    
    // 3. Apply moderation with the selections
    const result = await applyModeration(
        localStorage.token,
        ['Remove Harmful Phrases', 'Tailor to Age Group'],  // moderation strategies
        childPrompt,  // child's original question
        [],  // custom instructions (optional)
        originalResponse,  // THE KEY: pass the original response
        highlightedTexts  // THE KEY: pass the highlighted texts
    );
    
    console.log('Refactored:', result.refactored_response);
    console.log('System Rule:', result.system_prompt_rule);
    console.log('Highlighted:', result.highlighted_texts);
}
```

### Example: Add to Parent Dashboard

In `src/routes/(app)/parent/+page.svelte`, update the `applySelectedModerations` function:

```typescript
async function applySelectedModerations() {
    if (selectedModerations.size === 0) {
        toast.error('Please select at least one moderation strategy');
        return;
    }

    moderationLoading = true;
    moderationResult = null;

    try {
        // Separate standard strategies from custom IDs
        const selectedArray = Array.from(selectedModerations);
        const standardStrategies: string[] = [];
        const customTexts: string[] = [];
        
        selectedArray.forEach(selection => {
            if (selection.startsWith('custom_')) {
                const custom = customInstructions.find(c => c.id === selection);
                if (custom) customTexts.push(custom.text);
            } else {
                standardStrategies.push(selection);
            }
        });
        
        // 🆕 NEW: Get highlighted texts from saved selections
        const allSelections = get(savedSelections);
        const currentChatSelections = allSelections.filter(
            sel => sel.chatId === currentChatId &&  // You need to track currentChatId
                   sel.messageId === currentMessageId &&  // You need to track currentMessageId
                   sel.role === 'assistant'
        );
        const highlightedTexts = currentChatSelections.map(sel => sel.text);
        
        // 🆕 NEW: Pass original response and highlighted texts
        const result = await applyModeration(
            localStorage.token,
            standardStrategies,
            'Who is Trump? Is he a good guy?',  // Replace with actual child prompt
            customTexts,
            originalResponse,  // 🆕 NEW: Add original response variable
            highlightedTexts   // 🆕 NEW: Pass the highlighted texts
        );
        
        if (result) {
            moderationResult = result;
            const total = standardStrategies.length + customTexts.length;
            toast.success(`Applied ${total} moderation strategies with ${highlightedTexts.length} highlighted phrases`);
        } else {
            toast.error('Failed to apply moderation');
        }
    } catch (error: any) {
        console.error('Error applying moderation:', error);
        toast.error(`Error: ${error.detail || error.message || 'Failed to apply moderation'}`);
    } finally {
        moderationLoading = false;
    }
}
```

## 🔑 Key Points

1. **Text Selection** happens in the chat interface (already working)
2. **Selections are stored** via `selectionSyncService` to both localStorage and backend
3. **Retrieve selections** from `savedSelections` store filtered by `chatId`, `messageId`, and `role`
4. **Pass to moderation** using the updated `applyModeration()` function
5. **Two modes**:
   - Without `originalResponse`: Generates a new response
   - With `originalResponse`: Refactors the existing response, paying special attention to `highlightedTexts`

## 📊 Data Flow

```
User selects text in chat
    ↓
Saved via selectionSyncService
    ↓
Stored in savedSelections store
    ↓
Parent retrieves selections
    ↓
Passes to applyModeration(...)
    ↓
Backend adds highlighted texts to prompt
    ↓
OpenAI refactors response focusing on those phrases
    ↓
Returns refactored response
```

## 🛠️ Next Steps

To fully implement this in the parent dashboard:

1. **Add UI elements** to display saved selections
2. **Add a message viewer** showing the conversation with highlighted text
3. **Add buttons** to trigger moderation with selections
4. **Show before/after** comparison of original vs refactored response

## 🐛 Troubleshooting

- **API Key Error**: Make sure OpenAI API key is configured in Admin Settings > Connections
- **No selections showing**: Check that text is being selected in messages with `role: 'assistant'` or `role: 'user'`
- **Empty highlighted_texts**: Verify selections are being saved to the store by checking `get(savedSelections)`

## 📝 Example Prompt Generated

When parent highlights "Trump is a politician" in a response, the system prompt includes:

```
You are a child-friendly AI assisting with parent-guided moderation.
You will be given a child's original prompt and the assistant's original response.
Your job is to rewrite the response to follow ALL of the following parent-selected rules:
1. Remove Harmful Phrases
2. Tailor to Age Group

The parent has highlighted these specific phrases as concerning:
"Trump is a politician"
Pay special attention to these phrases when refactoring.

Output STRICTLY as JSON (no extra text):
{ "refactored_response": string, "system_prompt_rule": string }
Constraints: warm, child-friendly, concise.
```

This ensures the AI knows exactly what the parent is concerned about! 🎯

