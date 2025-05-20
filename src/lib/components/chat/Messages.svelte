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
import { tick, getContext, onMount, onDestroy, createEventDispatcher } from 'svelte';
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
export let autoScroll = true; // Default to true
let messagesCount = 20;
let messagesLoading = false;
let lastHistoryId = null;
// Add a specific flag to track streaming state
let isStreaming = false;
let scrollCheckInterval = null;
// Add variables to track content changes
let lastMessageContent = '';
let messageWatcher = null;
let activeScrollInterval = null;
// Simple optimization - split loading into chunks
const LOAD_CHUNK_SIZE = 5;
let loadedMessageCount = 0;
let loadingChunk = false;

import { tick } from 'svelte';

async function forceScrollToBottom() {
  await tick(); // Ensure the DOM is updated
  const container = document.getElementById('messages-container');
  if (!container) return;
  container.scrollTop = container.scrollHeight + 5000;
  setTimeout(() => {
    if (container) {
      container.scrollTop = container.scrollHeight + 5000;
    }
  }, 50);
}

// Called from parent when streaming starts
export function startMessageStream() {
  console.log("Stream started, enabling auto-scroll");
  isStreaming = true;
  autoScroll = true;
  
  // Clear any existing interval
  if (scrollCheckInterval) clearInterval(scrollCheckInterval);
  
  // Set up very frequent scrolling during streaming
  scrollCheckInterval = setInterval(() => {
    if (isStreaming && autoScroll) {
      forceScrollToBottom();
    }
  }, 100); // 10 times per second during streaming
  
  // Initial scroll
  forceScrollToBottom();
}

// Called from parent when streaming ends
export function endMessageStream() {
  console.log("Stream ended");
  isStreaming = false;
  
  // Final scrolls to make sure we're at the bottom
  (async () => {
    await forceScrollToBottom();
    setTimeout(forceScrollToBottom, 100);
    setTimeout(forceScrollToBottom, 300);
  })();
  
  // Clear the frequent interval
  if (scrollCheckInterval) {
    clearInterval(scrollCheckInterval);
    scrollCheckInterval = null;
  }
}

// Replace requestScrollToBottom with the more direct approach
function requestScrollToBottom() {
  if (autoScroll) {
    forceScrollToBottom();
  }
}

// Setup auto-scroll system
onMount(() => {
  const container = document.getElementById('messages-container');
  if (container) {
    container.addEventListener('scroll', () => {
      // If we're not streaming and user scrolls up, disable auto-scroll
      if (!isStreaming && container.scrollHeight - container.scrollTop > container.clientHeight + 200) {
        console.log("User scrolled away from bottom");
        autoScroll = false;
      }
      // If user scrolls to bottom, re-enable auto-scroll
      if (container.scrollHeight - container.scrollTop <= container.clientHeight + 50) {
        console.log("User scrolled to bottom");
        autoScroll = true;
      }
    });
  }
  
  // Set up a regular scrolling interval for when messages change
  activeScrollInterval = setInterval(() => {
    if (autoScroll && isStreaming) {
      forceScrollToBottom();
    }
  }, 500);
  
  return () => {
    if (activeScrollInterval) clearInterval(activeScrollInterval);
    if (messageWatcher) messageWatcher.disconnect();
    if (scrollCheckInterval) clearInterval(scrollCheckInterval);
  };
});

// Load messages in chunks for better performance
function loadNextChunk() {
  if (loadingChunk) return;
  loadingChunk = true;
  setTimeout(() => {
    loadedMessageCount += LOAD_CHUNK_SIZE;
    if (loadedMessageCount > messages.length) {
      loadedMessageCount = messages.length;
    }
    loadingChunk = false;
    
    // Force scroll after loading more content if needed
    if (autoScroll) {
      (async () => {
        await tick();
        await forceScrollToBottom();
      })();
    }
  }, 10);
}

const loadMoreMessages = async () => {
  // scroll slightly down to disable continuous loading
  const element = document.getElementById('messages-container');
  element.scrollTop = element.scrollTop + 100;
  messagesLoading = true;
  messagesCount += 20;
  await tick();
  messagesLoading = false;
};

// Update messages when history changes
$: if (history.currentId !== lastHistoryId) {
  let _messages = [];
  let message = history.messages[history.currentId];
  while (message && _messages.length <= messagesCount) {
    _messages.unshift({ ...message });
    message = message.parentId !== null ? history.messages[message.parentId] : null;
  }
  messages = _messages;
  lastHistoryId = history.currentId;
  // Show all messages immediately when new ones are added
  loadedMessageCount = messages.length;
  // Set auto-scroll when messages change
  autoScroll = true;
  // Force scroll to bottom with delay
  (async () => {
    await forceScrollToBottom();
    setTimeout(forceScrollToBottom, 100);
    setTimeout(forceScrollToBottom, 300);
  })();
}

// Track message changes and force scroll
$: if (messages.length > 0) {
  const lastMsg = messages[messages.length - 1];
  if (lastMsg && lastMsg.role === 'assistant') {
    if (autoScroll) {
      // Multiple scroll attempts to catch all updates
      (async () => {
        await forceScrollToBottom();
        setTimeout(forceScrollToBottom, 100);
        setTimeout(forceScrollToBottom, 300);
      })();
    }
    
    // If content is changing, we're likely streaming
    if (lastMsg.content !== lastMessageContent) {
      lastMessageContent = lastMsg.content;
      isStreaming = true;
      if (autoScroll) (async () => { await forceScrollToBottom(); })();
    }
  }
}

// Check if we need to load more messages
$: if (loadedMessageCount < messages.length && !loadingChunk) {
  loadNextChunk();
}

$: if (autoScroll && bottomPadding) {
  (async () => {
    await tick();
    await forceScrollToBottom();
  })();
}

// Update scroll functions to use the new method
const scrollToBottom = forceScrollToBottom;

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
forceScrollToBottom();
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
forceScrollToBottom();
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
forceScrollToBottom();
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
// Enable streaming mode when sending a new prompt
startMessageStream();
await sendPrompt(history, userPrompt, userMessageId);
// Multiple scroll attempts to ensure we catch all updates
forceScrollToBottom();
setTimeout(forceScrollToBottom, 500);
setTimeout(forceScrollToBottom, 1000);
setTimeout(forceScrollToBottom, 2000);
setTimeout(() => {
  endMessageStream();
  forceScrollToBottom();
}, 2500);
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
setTimeout(forceScrollToBottom, 100);
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
// Updated triggerScroll implementation
const triggerScroll = () => {
  console.log("Trigger scroll called");
  autoScroll = true;
  forceScrollToBottom();
  setTimeout(forceScrollToBottom, 100);
};
// When component is destroyed
onDestroy(() => {
  if (activeScrollInterval) clearInterval(activeScrollInterval);
  if (messageWatcher) messageWatcher.disconnect();
  if (scrollCheckInterval) clearInterval(scrollCheckInterval);
  if (window.scrollAnimationFrame) cancelAnimationFrame(window.scrollAnimationFrame);
  if (window.scrollVerificationFrame) cancelAnimationFrame(window.scrollVerificationFrame);
});
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
  <div class="w-full">
    {#if messages.at(0)?.parentId !== null}
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
    {#each messages.slice(0, loadedMessageCount) as message, messageIdx (message.id)}
      <Message
        {chatId}
        bind:history
        messageId={message.id}
        idx={messageIdx}
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
    {/each}
    {#if loadedMessageCount < messages.length}
      <div class="w-full flex justify-center py-2">
        <button
          class="bg-gray-100 dark:bg-gray-800 px-4 py-2 rounded-md text-sm"
          on:click={loadNextChunk}
        >
          Load more messages
        </button>
      </div>
    {/if}
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
