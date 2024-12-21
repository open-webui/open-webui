<script>
  import { getEnvVariables } from '$lib/utils/env';
  import { onMount } from 'svelte';

  let envVariables = [];
  let error = null;

  onMount(async () => {
    try {
      envVariables = await getEnvVariables();
    } catch (e) {
      error = e.message;
    }
  });
</script>

<style>
  .env-list {
    @apply space-y-2;
  }
  .env-item {
    @apply p-3 bg-gray-50 dark:bg-gray-850 rounded-lg;
  }
  .env-key {
    @apply font-medium text-gray-700 dark:text-gray-300;
  }
  .env-value {
    @apply text-gray-600 dark:text-gray-400;
  }
  .error {
    @apply p-3 text-red-700 bg-red-100 dark:bg-red-900 dark:text-red-100 rounded-lg;
  }
  .no-vars {
    @apply text-gray-600 dark:text-gray-400 italic;
  }
</style>

<form class="flex flex-col h-full justify-between space-y-3 text-sm">
  <div class="space-y-3 overflow-y-scroll scrollbar-hidden pr-2">
    <div>
      <div class="mb-1 text-sm font-medium">Environment Settings</div>
      
      {#if error}
        <div class="error">
          Error loading environment variables: {error}
        </div>
      {/if}

      {#if envVariables.length === 0}
        <p class="no-vars">No environment variables found.</p>
      {:else}
        <div class="env-list">
          {#each envVariables as { key, value }}
            <div class="env-item">
              <span class="env-key">{key}:</span>
              <span class="env-value">{value}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</form>
