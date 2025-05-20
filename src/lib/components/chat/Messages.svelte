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
import { tick, getContext, onMount, createEventDispatcher, afterUpdate } from 'svelte';
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
export let autoScroll = true;
let messagesCount = 20;
let messagesLoading = false;
let allMessagesLoaded = false;
let messagesContainer;
let lastMessageCount = 0;
let isGenerating = false;
let prevScrollTop = 0;

// More efficient message loading
const loadMoreMessages = async () => {
  if (messagesLoading || allMessagesLoaded) return;
  
  messagesLoading = true;
  // Store current scroll height and position for maintaining position
  const element = document.getElementById('messages-container');
  const oldScrollHeight = element ? element.scrollHeight : 0;
  const oldScrollTop = element ? element.scrollTop : 0;
  
  // Increase the number of messages to load
  messagesCount += 20;
  
  // Wait for DOM update
  await tick();
  
  // If there are still more messages to load, we're not at the top yet
  if (messages.length > 0 && messages[0]?.parentId !== null) {
    allMessagesLoaded = false;
  } else {
    allMessagesLoaded = true;
  }
  
  // Maintain scroll position after loading more messages
  if (element) {
    const newScrollHeight = element.scrollHeight;
    element.scrollTop = oldScrollTop + (newScrollHeight - oldScrollHeight);
  }
  
  messagesLoading = false;
};

// Message calculation - for a limited window of messages
$: if (history.currentId) {
  let _messages = [];
  let message = history.messages[history.currentId];
  let count = 0;
  
  // Build message array from current to past
  while (message && count < messagesCount) {
    _messages.unshift({ ...message });
    message = message.parentId !== null ? history.messages[message.parentId] : null;
    count++;
  }
  
  // Check if we've loaded all messages
  allMessagesLoaded = message === null;
  messages = _messages;
} else {
  messages = [];
  allMessagesLoaded = true;
}

// Track when messages change and auto-scroll if needed
$: {
  if (messages.length > lastMessageCount) {
    lastMessageCount = messages.length;
    if (autoScroll) {
      setTimeout(scrollToBottom, 10);
    }
  }
}

$: if (autoScroll && bottomPadding) {
  (async () => {
    await tick();
    scrollToBottom();
  })();
}

$: if (history.currentId) {
  // If message branch changes, we may need to scroll
  setTimeout(() => {
    const element = document.getElementById('messages-container');
    if (element && autoScroll) {
      element.scrollTop = element.scrollHeight;
    }
  }, 100);
}

// Simplified scroll handler to avoid interfering with native behavior
const handleScroll = (e) => {
  const container = e.target;
  
  // Check if we're near the top
  if (container.scrollTop < 300 && !messagesLoading && 
      messages.length > 0 && messages[0]?.parentId !== null) {
    loadMoreMessages();
  }
  
  // Only update autoScroll flag if we're not actively generating
  if (!isGenerating) {
    autoScroll = container.scrollHeight - container.scrollTop <= container.clientHeight + 100;
  }
};

const scrollToBottom = () => {
  requestAnimationFrame(() => {
    const element = document.getElementById('messages-container');
    if (element) {
      element.scrollTop = element.scrollHeight;
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

const triggerScroll = () => {
  isGenerating = true;
  const element = document.getElementById('messages-container');
  if (element) {
    // Check if we're already near the bottom
    autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 100;
    if (autoScroll) {
      requestAnimationFrame(() => {
        element.scrollTop = element.scrollHeight;
      });
    }
  }
  // Reset after a short delay
  setTimeout(() => {
    isGenerating = false;
  }, 500);
};

// Enhanced onMount function to ensure wheel events work properly
onMount(() => {
  messagesContainer = document.getElementById('messages-container');
  if (messagesContainer) {
    // Set initial scroll position to bottom
    setTimeout(scrollToBottom, 200);
    
    // Use our simplified scroll handler
    messagesContainer.addEventListener('scroll', handleScroll);
    
    // Ensure we're not blocking wheel events
    messagesContainer.addEventListener('wheel', (e) => {
      // Just let the natural scrolling happen, don't prevent default
      
      // We can update tracking variables if needed
      if (!messagesLoading && !isGenerating) {
        prevScrollTop = messagesContainer.scrollTop;
      }
    }, { passive: true }); // passive: true for better performance
    
    return () => {
      messagesContainer.removeEventListener('scroll', handleScroll);
      messagesContainer.removeEventListener('wheel', () => {});
    };
  }
});

// Ensure scroll behavior recovery if there are errors
afterUpdate(() => {
  const container = document.getElementById('messages-container');
  if (container) {
    // Ensure scrolling is enabled
    container.style.overflow = 'auto';
  }
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
    <div class="w-full pt-2 h-full">
      {#key chatId}
        <div id="messages-container" class="w-full h-full overflow-auto">
          {#if messages.length > 0 && !allMessagesLoaded}
            <div class="w-full flex justify-center py-2 text-xs items-center gap-2 sticky top-0 bg-white dark:bg-gray-900 z-10">
              {#if messagesLoading}
                <Spinner className="size-4" />
                <div class="animate-pulse">Loading older messages...</div>
              {:else}
                <button on:click={loadMoreMessages} class="px-3 py-1.5 text-xs rounded bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700">
                  Load more messages
                </button>
              {/if}
            </div>
          {/if}
          
          {#each messages as message, messageIdx (message.id)}
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
              triggerScroll={triggerScroll}
              {readOnly}
            />
          {/each}
          
          <div class="pb-12"></div>
          {#if bottomPadding}
            <div class="pb-6"></div>
          {/if}
        </div>
      {/key}
    </div>
  {/if}
</div>

<style>
  :global(div[id="messages-container"]) {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow-y: auto;
    scroll-behavior: smooth;
    touch-action: pan-y;
  }
  
  /* Ensure the container elements don't shrink */
  :global(div[id="messages-container"] > *) {
    flex-shrink: 0;
  }
</style>
