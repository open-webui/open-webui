<script lang="ts">
import { v4 as uuidv4 } from 'uuid';
import {
chats,
config,
settings,
user as _user,
mobile,
currentChatPage,
temporaryChatEnabled
} from '$lib/stores';
import { tick, getContext, onMount, createEventDispatcher } from 'svelte';
const dispatch = createEventDispatcher();
import { toast } from 'svelte-sonner';
import { getChatList, updateChatById } from '$lib/apis/chats';
import { copyToClipboard, extractCurlyBraceWords } from '$lib/utils';
import Message from './Messages/Message.svelte';
import Loader from '../common/Loader.svelte';
import Spinner from '../common/Spinner.svelte';
import ChatPlaceholder from './ChatPlaceholder.svelte';
const i18n = getContext('i18n');
export let className = 'h-full flex pt-8';
export let chatId = '';
export let user = $_user;
export let prompt;
export let history = {};
export let selectedModels;
export let atSelectedModel;
let messages = [];
export let sendPrompt: Function;
export let continueResponse: Function;
export let regenerateResponse: Function;
export let mergeResponses: Function;
export let chatActionHandler: Function;
export let showMessage: Function = () => {};
export let submitMessage: Function = () => {};
export let addMessages: Function = () => {};
export let readOnly = false;
export let bottomPadding = false;
export let autoScroll;
let messagesCount = 20;
let messagesLoading = false;
let lastHistoryId = null; // Track the last history ID we processed

// Add these virtualization variables
let visibleMessages = [];
let messageHeights = {}; // Store actual heights of messages
let totalHeight = 0;
let scrollPosition = 0;
let containerHeight = 0;
let estimatedMessageHeight = 300; // Increase default estimate to prevent initial overlap

// Add this action for height measurement
function measureHeight(node, messageId) {
  function measure() {
    const height = node.clientHeight;
    if (height > 0 && messageHeights[messageId] !== height) {
      messageHeights[messageId] = height;
      updateVisibleMessages();
    }
  }

  // Set up ResizeObserver for dynamic height changes
  const resizeObserver = new ResizeObserver(() => {
    measure();
  });
  
  resizeObserver.observe(node);
  measure(); // Initial measurement
  
  return {
    destroy() {
      resizeObserver.disconnect();
    },
    update(newMessageId) {
      messageId = newMessageId;
      measure();
    }
  };
}

// Calculate positions based on actual measured heights
function calculateMessagePositions() {
  let positions = {};
  let currentPosition = 0;
  
  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    positions[msg.id] = currentPosition;
    // Use known height or estimate
    const height = messageHeights[msg.id] || estimatedMessageHeight;
    currentPosition += height + 10; // Add 10px gap between messages
  }
  
  totalHeight = currentPosition;
  return positions;
}

// Update visible messages with better position calculation
function updateVisibleMessages() {
  const container = document.getElementById('messages-container');
  if (!container) return;
  
  scrollPosition = container.scrollTop;
  containerHeight = container.clientHeight;
  
  const positions = calculateMessagePositions();
  
  // Find visible messages based on position
  visibleMessages = messages.filter((msg) => {
    const position = positions[msg.id];
    const height = messageHeights[msg.id] || estimatedMessageHeight;
    return (position < scrollPosition + containerHeight + 500) && 
           (position + height > scrollPosition - 500);
  }).map(msg => ({
    message: msg,
    index: messages.indexOf(msg),
    position: positions[msg.id]
  }));
}

// Force rebuild messages from history
function rebuildMessages() {
  if (history.currentId) {
    let _messages = [];
    let message = history.messages[history.currentId];
    while (message && _messages.length <= messagesCount) {
      _messages.unshift({ ...message });
      message = message.parentId !== null ? history.messages[message.parentId] : null;
    }
    messages = _messages;
    lastHistoryId = history.currentId;
    
    // Schedule update of visible messages and auto-scroll
    setTimeout(() => {
      updateVisibleMessages();
      if (autoScroll) {
        setTimeout(scrollToBottom, 50);
      }
    }, 0);
  } else {
    messages = [];
    lastHistoryId = null;
  }
}

onMount(() => {
  const container = document.getElementById('messages-container');
  if (container) {
    container.addEventListener('scroll', () => {
      updateVisibleMessages();
    });
    // Initial update
    setTimeout(updateVisibleMessages, 100);
  }
  
  return () => {
    if (container) {
      container.removeEventListener('scroll', updateVisibleMessages);
    }
  };
});

const loadMoreMessages = async () => {
// scroll slightly down to disable continuous loading
const element = document.getElementById('messages-container');
element.scrollTop = element.scrollTop + 100;
messagesLoading = true;
messagesCount += 20;
await tick();
messagesLoading = false;
};

// Watch history changes - critically important for follow-up questions
$: if (history.currentId !== lastHistoryId) {
  rebuildMessages();
}

// Update visible messages when messages change
$: if (messages && messages.length > 0) {
  setTimeout(() => {
    updateVisibleMessages();
    
    // If autoScroll is enabled, scroll to the newest message
    if (autoScroll) {
      setTimeout(scrollToBottom, 0);
    }
  }, 0);
}

// Add this reactive statement to trigger scroll when visible messages change
$: if (visibleMessages.length > 0 && autoScroll) {
  const lastMessage = visibleMessages[visibleMessages.length - 1].message;
  
  // If the last visible message is also the last in the full messages array, 
  // scroll to bottom (handles auto-scrolling during message generation)
  if (lastMessage && lastMessage.id === messages[messages.length - 1]?.id) {
    setTimeout(scrollToBottom, 0);
  }
}

$: if (autoScroll && bottomPadding) {
(async () => {
await tick();
scrollToBottom();
})();
}

// Update scrollToBottom function to work with virtualization
const scrollToBottom = () => {
  requestAnimationFrame(() => {
    const container = document.getElementById('messages-container');
    if (container) {
      container.scrollTop = totalHeight + 1000; // Use our calculated total height plus extra to ensure we're at bottom
    }
  });
};

const updateChat = async () => {
if (!$temporaryChatEnabled) {
history = history;
await tick();
await updateChatById(localStorage.token, chatId, {
history: history,
messages: messages
});
currentChatPage.set(1);
await chats.set(await getChatList(localStorage.token, $currentChatPage));
}
};
const gotoMessage = async (message, idx) => {
// Determine the correct sibling list (either parent's children or root messages)
let siblings;
if (message.parentId !== null) {
siblings = history.messages[message.parentId].childrenIds;
} else {
siblings = Object.values(history.messages)
.filter((msg) => msg.parentId === null)
.map((msg) => msg.id);
}
// Clamp index to a valid range
idx = Math.max(0, Math.min(idx, siblings.length - 1));
let messageId = siblings[idx];
// If we're navigating to a different message
if (message.id !== messageId) {
// Drill down to the deepest child of that branch
let messageChildrenIds = history.messages[messageId].childrenIds;
while (messageChildrenIds.length !== 0) {
messageId = messageChildrenIds.at(-1);
messageChildrenIds = history.messages[messageId].childrenIds;
}
history.currentId = messageId;
}
await tick();
// Optional auto-scroll
if ($settings?.scrollOnBranchChange ?? true) {
const element = document.getElementById('messages-container');
autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
setTimeout(() => {
scrollToBottom();
}, 100);
}
};
const showPreviousMessage = async (message) => {
if (message.parentId !== null) {
let messageId =
history.messages[message.parentId].childrenIds[
Math.max(history.messages[message.parentId].childrenIds.indexOf(message.id) - 1, 0)
];
if (message.id !== messageId) {
let messageChildrenIds = history.messages[messageId].childrenIds;
while (messageChildrenIds.length !== 0) {
messageId = messageChildrenIds.at(-1);
messageChildrenIds = history.messages[messageId].childrenIds;
}
history.currentId = messageId;
}
} else {
let childrenIds = Object.values(history.messages)
.filter((message) => message.parentId === null)
.map((message) => message.id);
let messageId = childrenIds[Math.max(childrenIds.indexOf(message.id) - 1, 0)];
if (message.id !== messageId) {
let messageChildrenIds = history.messages[messageId].childrenIds;
while (messageChildrenIds.length !== 0) {
messageId = messageChildrenIds.at(-1);
messageChildrenIds = history.messages[messageId].childrenIds;
}
history.currentId = messageId;
}
}
await tick();
if ($settings?.scrollOnBranchChange ?? true) {
const element = document.getElementById('messages-container');
autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
setTimeout(() => {
scrollToBottom();
}, 100);
}
};
const showNextMessage = async (message) => {
if (message.parentId !== null) {
let messageId =
history.messages[message.parentId].childrenIds[
Math.min(
history.messages[message.parentId].childrenIds.indexOf(message.id) + 1,
history.messages[message.parentId].childrenIds.length - 1
)
];
if (message.id !== messageId) {
let messageChildrenIds = history.messages[messageId].childrenIds;
while (messageChildrenIds.length !== 0) {
messageId = messageChildrenIds.at(-1);
messageChildrenIds = history.messages[messageId].childrenIds;
}
history.currentId = messageId;
}
} else {
let childrenIds = Object.values(history.messages)
.filter((message) => message.parentId === null)
.map((message) => message.id);
let messageId =
childrenIds[Math.min(childrenIds.indexOf(message.id) + 1, childrenIds.length - 1)];
if (message.id !== messageId) {
let messageChildrenIds = history.messages[messageId].childrenIds;
while (messageChildrenIds.length !== 0) {
messageId = messageChildrenIds.at(-1);
messageChildrenIds = history.messages[messageId].childrenIds;
}
history.currentId = messageId;
}
}
await tick();
if ($settings?.scrollOnBranchChange ?? true) {
const element = document.getElementById('messages-container');
autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
setTimeout(() => {
scrollToBottom();
}, 100);
}
};
const rateMessage = async (messageId, rating) => {
history.messages[messageId].annotation = {
...history.messages[messageId].annotation,
rating: rating
};
await updateChat();
};
const editMessage = async (messageId, { content, files }, submit = true) => {
if (history.messages[messageId].role === 'user') {
if (submit) {
// New user message
let userPrompt = content;
let userMessageId = uuidv4();
let userMessage = {
id: userMessageId,
parentId: history.messages[messageId].parentId,
childrenIds: [],
role: 'user',
content: userPrompt,
...(files && { files: files }),
models: selectedModels,
timestamp: Math.floor(Date.now() / 1000) // Unix epoch
};
let messageParentId = history.messages[messageId].parentId;
if (messageParentId !== null) {
history.messages[messageParentId].childrenIds = [
...history.messages[messageParentId].childrenIds,
userMessageId
];
}
history.messages[userMessageId] = userMessage;
history.currentId = userMessageId;
await tick();
await sendPrompt(history, userPrompt, userMessageId);
} else {
// Edit user message
history.messages[messageId].content = content;
history.messages[messageId].files = files;
await updateChat();
}
} else {
if (submit) {
// New response message
const responseMessageId = uuidv4();
const message = history.messages[messageId];
const parentId = message.parentId;
const responseMessage = {
...message,
id: responseMessageId,
parentId: parentId,
childrenIds: [],
files: undefined,
content: content,
timestamp: Math.floor(Date.now() / 1000) // Unix epoch
};
history.messages[responseMessageId] = responseMessage;
history.currentId = responseMessageId;
// Append messageId to childrenIds of parent message
if (parentId !== null) {
history.messages[parentId].childrenIds = [
...history.messages[parentId].childrenIds,
responseMessageId
];
}
await updateChat();
} else {
// Edit response message
history.messages[messageId].originalContent = history.messages[messageId].content;
history.messages[messageId].content = content;
await updateChat();
}
}
};
const actionMessage = async (actionId, message, event = null) => {
await chatActionHandler(chatId, actionId, message.model, message.id, event);
};
const saveMessage = async (messageId, message) => {
history.messages[messageId] = message;
await updateChat();
};
const deleteMessage = async (messageId) => {
const messageToDelete = history.messages[messageId];
const parentMessageId = messageToDelete.parentId;
const childMessageIds = messageToDelete.childrenIds ?? [];
// Collect all grandchildren
const grandchildrenIds = childMessageIds.flatMap(
(childId) => history.messages[childId]?.childrenIds ?? []
);
// Update parent's children
if (parentMessageId && history.messages[parentMessageId]) {
history.messages[parentMessageId].childrenIds = [
...history.messages[parentMessageId].childrenIds.filter((id) => id !== messageId),
...grandchildrenIds
];
}
// Update grandchildren's parent
grandchildrenIds.forEach((grandchildId) => {
if (history.messages[grandchildId]) {
history.messages[grandchildId].parentId = parentMessageId;
}
});
// Delete the message and its children
[messageId, ...childMessageIds].forEach((id) => {
delete history.messages[id];
});
await tick();
showMessage({ id: parentMessageId });
// Update the chat
await updateChat();
};

// Make triggerScroll compatible with virtualization
const triggerScroll = () => {
  const container = document.getElementById('messages-container');
  
  if (container) {
    // Check if we're near the bottom
    const isNearBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 100;
    
    // If we're near the bottom, enable auto-scrolling
    autoScroll = isNearBottom;
    
    if (autoScroll) {
      setTimeout(scrollToBottom, 50);
    }
  }
};
</script>
<div class={className}>
{#if Object.keys(history?.messages ?? {}).length == 0}
<ChatPlaceholder
modelIds={selectedModels}
{atSelectedModel}
submitPrompt={async (p) => {
let text = p;
if (p.includes('{{CLIPBOARD}}')) {
const clipboardText = await navigator.clipboard.readText().catch((err) => {
toast.error($i18n.t('Failed to read clipboard contents'));
return '{{CLIPBOARD}}';
});
text = p.replaceAll('{{CLIPBOARD}}', clipboardText);
}
prompt = text;
await tick();
}}
/>
{:else}
<div class="w-full pt-2">
{#key chatId}
<div id="messages-container" class="w-full overflow-y-auto h-full">
  <!-- Spacer for scrolling with correct total height -->
  <div style="height: {totalHeight}px; position: relative;">
    {#if messages.at(0)?.parentId !== null && scrollPosition < estimatedMessageHeight}
      <Loader
        on:visible={(e) => {
          console.log('visible');
          if (!messagesLoading) {
            loadMoreMessages();
          }
        }}
      >
        <div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
          <Spinner className=" size-4" />
          <div class=" ">Loading...</div>
        </div>
      </Loader>
    {/if}
    
    {#each visibleMessages as item (item.message.id)}
      <div 
        style="position: absolute; width: 100%; top: {item.position}px;"
        id="msg-{item.message.id}" 
        use:measureHeight={item.message.id}
      >
        <Message
          {chatId}
          bind:history
          messageId={item.message.id}
          idx={item.index}
          {user}
          {gotoMessage}
          {showPreviousMessage}
          {showNextMessage}
          {updateChat}
          {editMessage}
          {deleteMessage}
          {rateMessage}
          {actionMessage}
          {saveMessage}
          {submitMessage}
          {regenerateResponse}
          {continueResponse}
          {mergeResponses}
          {addMessages}
          {triggerScroll}
          {readOnly}
        />
      </div>
    {/each}
  </div>
  
  <div class="pb-12" />
  {#if bottomPadding}
    <div class="pb-6" />
  {/if}
</div>
{/key}
</div>
{/if}
</div>
