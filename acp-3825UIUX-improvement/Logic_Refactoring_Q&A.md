# Question
The buttons for search plan agent should only appear, when the following conditions are met: 
1. The last message on a chat is a model response, not a user message. 
2. The model's response contain the text matching environment variable SEARCH_PLAN_AGENT_BUTTONS_TRIGGERING_SENTENCE 
3. Buttons haven't been clicked before (only in current frontend session, storing button clicking state outside of frontend is never considered, and will never be), as clicking on those buttons will make them disappear, to prevent buttons from being able to be clicked more than once. 

The current implementation does this condition check / button clicked state control at ResponseMessage level, which make things unnecessarily complicated. I want to change it manage condition / state at chat level, instead of ResponseMessage level, so the entire chat only has to manage 1 state across the entire chat history of that chat, and condition check / state management only needs to occur once when user clicked into the chat, or model made a response, rather than needed to iterate through each ResponseMessage every time. 

I don't mind if buttons reappear if user clicked away to another chat and back. The state can completely reset when that happens.
# Answer
Based on my analysis of the current implementation, I can see exactly what needs to be changed to move from message-level to chat-level management of search plan agent buttons.

Current Implementation Analysis
-------------------------------

The current implementation manages the search plan agent buttons at the individual message level. The condition checking occurs in `ResponseMessage.svelte` where buttons are shown when all conditions are met: ResponseMessage.svelte:881

Each `ResponseMessage` component maintains its own `showCorrectionButtons` state: ResponseMessage.svelte:139

The current approach sets up event listeners in each message component's `onMount` to handle the `correctionSubmitted` event: ResponseMessage.svelte:562-566

When buttons are clicked, they set `showCorrectionButtons = false` to hide themselves: ResponseMessage.svelte:901

The configuration for the triggering sentence and button mapping is defined in the backend config: config.py:1162-1175

Recommended Chat-Level Refactoring
----------------------------------

### 1\. Move State to Chat Component

Add a single chat-level state variable in `Chat.svelte` where the main chat history is managed: Chat.svelte:130-133

```

```
let showSearchPlanButtons = false;
```

```

### 2\. Implement Chat-Level Condition Checking

Create a function in `Chat.svelte` that checks the three conditions:

-   Last message is a model response
-   Contains the triggering sentence
-   Buttons haven't been clicked in current session

Call this function:

-   When loading a chat (similar to how other chat state is initialized)
-   After a message is completed (similar to the completion handling): Chat.svelte:1202-1242

### 3\. Handle Events at Chat Level

Move the `correctionSubmitted` event handling from individual message components to the chat level. The event is already being dispatched from `MessageInput.svelte`: MessageInput.svelte:105-109

Set up the event listener in `Chat.svelte`'s `onMount`, similar to how other chat-level events are handled: Chat.svelte:402-405

### 4\. Pass State Down to Messages

Modify the `Messages` component to receive the chat-level `showSearchPlanButtons` state and pass it down to `ResponseMessage` components, replacing the individual message-level state management.

### 5\. Simplify ResponseMessage Logic

Update the condition in `ResponseMessage.svelte` to remove the complex per-message state management and simply use the passed-down chat-level state along with the basic message content check.

Benefits of This Approach
-------------------------

1.  **Simplified State Management**: Single source of truth for button visibility
2.  **Reduced Complexity**: No need for individual event listeners in each message component
3.  **Better Performance**: Condition checking happens only once per chat load/message completion, not on every render
4.  **Session-Based Reset**: Buttons naturally reappear when user navigates away and back, as requested
5.  **Easier Maintenance**: All search plan button logic centralized in one location

This refactoring will significantly simplify the architecture while meeting your requirement for chat-level state management and allowing buttons to reappear when users navigate between chats.

Notes
-----

The current implementation uses a complex per-message approach with event handling that was likely designed for more granular control. However, since the requirement is to show buttons only for the last message and hide them globally once clicked, a chat-level approach is much more appropriate and will reduce the codebase complexity significantly.

Relevant files:
1. @/src/lib/components/chat/Messages/ResponseMessage.svelte 
2. @/src\lib\components\chat\MessageInput.svelte 
3. @/backend\open_webui\config.py
4. @/src\lib\components\chat\Chat.svelte