<script lang="ts">
  import { toast } from 'svelte-sonner';

  import { tick, getContext, onMount, createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();
  const i18n = getContext('i18n');

  import { settings } from '$lib/stores';
  import { copyToClipboard } from '$lib/utils';

  import MultiResponseMessages from './MultiResponseMessages.svelte';
  import ResponseMessage from './ResponseMessage.svelte';
  import UserMessage from './UserMessage.svelte';







  interface Props {
    chatId: any;
    idx?: number;
    history: any;
    messageId: any;
    user: any;
    showPreviousMessage: any;
    showNextMessage: any;
    updateChat: any;
    editMessage: any;
    saveMessage: any;
    deleteMessage: any;
    rateMessage: any;
    actionMessage: any;
    submitMessage: any;
    regenerateResponse: any;
    continueResponse: any;
    mergeResponses: any;
    addMessages: any;
    triggerScroll: any;
    readOnly?: boolean;
  }

  let {
    chatId,
    idx = 0,
    history = $bindable(),
    messageId,
    user,
    showPreviousMessage,
    showNextMessage,
    updateChat,
    editMessage,
    saveMessage,
    deleteMessage,
    rateMessage,
    actionMessage,
    submitMessage,
    regenerateResponse,
    continueResponse,
    mergeResponses,
    addMessages,
    triggerScroll,
    readOnly = false
  }: Props = $props();
</script>

<div
  class="flex flex-col justify-between px-5 mb-3 w-full {($settings?.widescreenMode ?? null)
    ? 'max-w-full'
    : 'max-w-5xl'} mx-auto rounded-lg group"
>
  {#if history.messages[messageId]}
    {#if history.messages[messageId].role === 'user'}
      <UserMessage
        {deleteMessage}
        {editMessage}
        {history}
        isFirstMessage={idx === 0}
        {messageId}
        {readOnly}
        {showNextMessage}
        {showPreviousMessage}
        siblings={history.messages[messageId].parentId !== null
          ? (history.messages[history.messages[messageId].parentId]?.childrenIds ?? [])
          : (Object.values(history.messages)
            .filter((message) => message.parentId === null)
            .map((message) => message.id) ?? [])}
        {user}
      />
    {:else if (history.messages[history.messages[messageId].parentId]?.models?.length ?? 1) === 1}
      <ResponseMessage
        {actionMessage}
        {addMessages}
        {chatId}
        {continueResponse}
        {deleteMessage}
        {editMessage}
        {history}
        isLastMessage={messageId === history.currentId}
        {messageId}
        {rateMessage}
        {readOnly}
        {regenerateResponse}
        {saveMessage}
        {showNextMessage}
        {showPreviousMessage}
        siblings={history.messages[history.messages[messageId].parentId]?.childrenIds ?? []}
        {submitMessage}
        {updateChat}
      />
    {:else}
      <MultiResponseMessages
        {actionMessage}
        {addMessages}
        {chatId}
        {continueResponse}
        {deleteMessage}
        {editMessage}
        isLastMessage={messageId === history?.currentId}
        {mergeResponses}
        {messageId}
        {rateMessage}
        {readOnly}
        {regenerateResponse}
        {saveMessage}
        {submitMessage}
        {triggerScroll}
        {updateChat}
        bind:history
      />
    {/if}
  {/if}
</div>
