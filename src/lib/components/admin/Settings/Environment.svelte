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
  .settings-section {
    @apply space-y-4;
  }
  .settings-header {
    @apply text-xl font-semibold text-gray-900 dark:text-gray-100;
  }
  .env-list {
    @apply space-y-2;
  }
  .env-item {
    @apply p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700;
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

<div class="settings-section">
  <h2 class="settings-header">Environment Settings</h2>
  
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
