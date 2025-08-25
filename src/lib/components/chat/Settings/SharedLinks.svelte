<script lang="ts">
  import { onMount } from 'svelte';
  import { getSharedChats } from '$lib/apis/chats';
  import { config } from '$lib/stores';

  let sharedChats = [];

  onMount(async () => {
    sharedChats = await getSharedChats(localStorage.token);
  });
</script>

<div class="flex flex-col h-full">
  <div class="text-lg font-medium">Shared Links</div>
  <div class="mt-4 space-y-2 overflow-y-auto">
    {#if sharedChats.length > 0}
      {#each sharedChats as chat}
        <div class="p-2 border rounded-lg">
          <div class="font-medium">{chat.title}</div>
          <div class="text-sm text-gray-500">
            <a href={`/s/${chat.id}`} target="_blank" rel="noopener noreferrer">
              {`${$config.WEBUI_URL}/s/${chat.id}`}
            </a>
          </div>
        </div>
      {/each}
    {:else}
      <div class="text-center text-gray-500">You haven't shared any chats yet.</div>
    {/if}
  </div>
</div>
