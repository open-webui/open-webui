<script>
  import { getEnvVariables } from '$lib/utils/env';
  import { onMount, getContext, createEventDispatcher } from 'svelte';

const dispatch = createEventDispatcher();

	import Switch from '$lib/components/common/Switch.svelte';
  import { getRAGConfig, updateRAGConfig } from '$lib/apis/retrieval';

  let envVariables = [];
  let error = null;
  let enableGoogleDriveIntegration = false;

  const i18n = getContext('i18n');

  const submitHandler = async () => {
		const res = await updateRAGConfig(localStorage.token, {
			enable_google_drive_integration: enableGoogleDriveIntegration,
		});
		dispatch('save');
	};

  onMount(async () => {
    const res = await getRAGConfig(localStorage.token);
    enableGoogleDriveIntegration = res.enable_google_drive_integration;

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

<form class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
	}}
>

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

    <hr class=" dark:border-gray-850" />

    <div class="text-sm font-medium mb-1">{$i18n.t('Google Drive')}</div>

    <div class="">
      <div class="flex justify-between items-center text-xs">
        <div class="text-xs font-medium">{$i18n.t('Enable Google Drive')}</div>
        <div>
          <Switch bind:state={enableGoogleDriveIntegration} />
        </div>
      </div>
    </div>

    <hr class=" dark:border-gray-850" />
    <div class="flex justify-end pt-3 text-sm font-medium">
      <button
        class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
        type="submit"
      >
        {$i18n.t('Save')}
      </button>
    </div>
  
  </div>
</form>
