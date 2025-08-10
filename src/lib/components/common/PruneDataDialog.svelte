<script lang="ts">
  import { createEventDispatcher, getContext } from 'svelte';
  import Modal from '$lib/components/common/Modal.svelte';
  import Switch from '$lib/components/common/Switch.svelte';

  const i18n = getContext('i18n');

  export let show = false;

  let deleteChatsByAge = false;
  let days = 60;
  let exempt_archived_chats = true;
  let exempt_chats_in_folders = false;
  
  // Orphaned resource deletion toggles
  let delete_orphaned_chats = true;
  let delete_orphaned_tools = false;
  let delete_orphaned_functions = false;
  let delete_orphaned_prompts = true;
  let delete_orphaned_knowledge_bases = true;
  let delete_orphaned_models = true;
  let delete_orphaned_notes = true;
  let delete_orphaned_folders = true;
  
  let showDetailsExpanded = false;
  let activeDetailsTab = 'chats';
  let activeSettingsTab = 'chats';
  let showApiPreview = false;

  const dispatch = createEventDispatcher();

  const confirm = () => {
    dispatch('confirm', { 
      days: deleteChatsByAge ? days : null, 
      exempt_archived_chats,
      exempt_chats_in_folders,
      delete_orphaned_chats,
      delete_orphaned_tools,
      delete_orphaned_functions,
      delete_orphaned_prompts,
      delete_orphaned_knowledge_bases,
      delete_orphaned_models,
      delete_orphaned_notes,
      delete_orphaned_folders
    });
    show = false;
  };

  // Generate API call preview
  $: apiCallPreview = `POST /api/v1/admin/prune
Content-Type: application/json
Authorization: Bearer <your-api-key>

{
  "days": ${deleteChatsByAge ? days : null},
  "exempt_archived_chats": ${exempt_archived_chats},
  "exempt_chats_in_folders": ${exempt_chats_in_folders},
  "delete_orphaned_chats": ${delete_orphaned_chats},
  "delete_orphaned_tools": ${delete_orphaned_tools},
  "delete_orphaned_functions": ${delete_orphaned_functions},
  "delete_orphaned_prompts": ${delete_orphaned_prompts},
  "delete_orphaned_knowledge_bases": ${delete_orphaned_knowledge_bases},
  "delete_orphaned_models": ${delete_orphaned_models},
  "delete_orphaned_notes": ${delete_orphaned_notes},
  "delete_orphaned_folders": ${delete_orphaned_folders}
}`;

  const copyApiCall = () => {
    navigator.clipboard.writeText(apiCallPreview).then(() => {
      // Could add a toast notification here
      console.log('API call copied to clipboard');
    }).catch(err => {
      console.error('Failed to copy API call: ', err);
    });
  };
</script>

<Modal bind:show size="lg">
  <div>
    <div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
      <div class="text-lg font-medium self-center">
        {$i18n.t('Prune Orphaned Data')}
      </div>
      <button
        class="self-center"
        on:click={() => {
          show = false;
        }}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          class="w-5 h-5"
        >
          <path
            d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
          />
        </svg>
      </button>
    </div>

    <div class="flex flex-col w-full px-5 pb-5 dark:text-gray-200">
      <div class="space-y-4">
        <!-- Critical Warning Message -->
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3 flex-1">
              <h3 class="text-sm font-medium text-red-800 dark:text-red-200 mb-2">
                {$i18n.t('Destructive Operation - Backup Recommended')}
              </h3>
              <div class="text-sm text-red-700 dark:text-red-300 space-y-1">
                <p>{$i18n.t('This action will permanently delete data from your database. Only orphaned or old data, based on your configuration settings, will be deleted. All active, referenced data remains completely safe.')}</p>
                <p>{$i18n.t('This operation cannot be undone. Create a complete backup of your database and files before proceeding. This operation is performed entirely at your own risk - having a backup ensures you can restore any data if something unexpected occurs.')}</p>
                
                <!-- Expandable Details Section -->
                <div class="mt-3">
                  <button
                    class="flex items-center text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 focus:outline-none"
                    on:click={() => showDetailsExpanded = !showDetailsExpanded}
                  >
                    <svg 
                      class="w-3 h-3 mr-1 transition-transform duration-200 {showDetailsExpanded ? 'rotate-90' : ''}" 
                      fill="currentColor" 
                      viewBox="0 0 20 20"
                    >
                      <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                    </svg>
                    {showDetailsExpanded ? $i18n.t('Hide details') : $i18n.t('Show details')}
                  </button>
                  
                  {#if showDetailsExpanded}
                    <div class="mt-2 pl-4 border-l-2 border-red-300 dark:border-red-700 text-xs text-red-600 dark:text-red-400">
                      <p class="mb-3"><strong>{$i18n.t('Note:')}</strong> {$i18n.t('This list provides an overview of what will be deleted during the pruning process and may not be complete or fully up-to-date.')}</p>
                      
                      <!-- Tab Navigation -->
                      <div class="flex flex-wrap gap-1 mb-3 border-b border-red-300 dark:border-red-700">
                        <button
                          class="px-2 py-1 text-xs font-medium rounded-t transition-colors {activeDetailsTab === 'chats' ? 'bg-red-100 dark:bg-red-800 text-red-800 dark:text-red-200' : 'text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200'}"
                          on:click={() => activeDetailsTab = 'chats'}
                        >
                          {$i18n.t('Chats')}
                        </button>
                        <button
                          class="px-2 py-1 text-xs font-medium rounded-t transition-colors {activeDetailsTab === 'workspace' ? 'bg-red-100 dark:bg-red-800 text-red-800 dark:text-red-200' : 'text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200'}"
                          on:click={() => activeDetailsTab = 'workspace'}
                        >
                          {$i18n.t('Workspace')}
                        </button>
                        <button
                          class="px-2 py-1 text-xs font-medium rounded-t transition-colors {activeDetailsTab === 'datavector' ? 'bg-red-100 dark:bg-red-800 text-red-800 dark:text-red-200' : 'text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200'}"
                          on:click={() => activeDetailsTab = 'datavector'}
                        >
                          {$i18n.t('Data & Vector')}
                        </button>
                        <button
                          class="px-2 py-1 text-xs font-medium rounded-t transition-colors {activeDetailsTab === 'imagesaudio' ? 'bg-red-100 dark:bg-red-800 text-red-800 dark:text-red-200' : 'text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200'}"
                          on:click={() => activeDetailsTab = 'imagesaudio'}
                        >
                          {$i18n.t('Images & Audio')}
                        </button>
                        <button
                          class="px-2 py-1 text-xs font-medium rounded-t transition-colors {activeDetailsTab === 'system' ? 'bg-red-100 dark:bg-red-800 text-red-800 dark:text-red-200' : 'text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200'}"
                          on:click={() => activeDetailsTab = 'system'}
                        >
                          {$i18n.t('System & Database')}
                        </button>
                      </div>

                      <!-- Tab Content -->
                      <div class="space-y-2">
                        {#if activeDetailsTab === 'chats'}
                          <div class="space-y-1">
                            <p><strong>{$i18n.t('Age-Based Chat Deletion:')}</strong></p>
                            <p>• {$i18n.t('Removes conversations older than specified days based on when they were last modified or updated (not when they were created)')}</p>
                            <p>• {$i18n.t('Supports exemptions for:')}</p>
                            <p class="ml-4">◦ {$i18n.t('Archived chats')}</p>
                            <p class="ml-4">◦ {$i18n.t('Chats organized in folders and pinned chats')}</p>
                            
                            <p class="pt-2"><strong>{$i18n.t('Orphaned Content Cleanup:')}</strong></p>
                            <p>• {$i18n.t('Delete orphaned chats from deleted users')}</p>
                            <p>• {$i18n.t('Delete orphaned folders from deleted users')}</p>
                          </div>
                        {:else if activeDetailsTab === 'workspace'}
                          <div class="space-y-1">
                            <p><strong>{$i18n.t('Orphaned Workspace Items from Deleted Users:')}</strong></p>
                            <p>• {$i18n.t('Delete orphaned knowledge bases')}</p>
                            <p>• {$i18n.t('Delete orphaned custom tools')}</p>
                            <p>• {$i18n.t('Delete orphaned custom functions (Actions, Pipes, Filters)')}</p>
                            <p>• {$i18n.t('Delete orphaned custom prompts and templates')}</p>
                            <p>• {$i18n.t('Delete orphaned custom models and configurations')}</p>
                            <p>• {$i18n.t('Delete orphaned notes')}</p>
                          </div>
                        {:else if activeDetailsTab === 'datavector'}
                          <div class="space-y-1">
                            <p><strong>{$i18n.t('Files & Vector Storage:')}</strong></p>
                            <p>• {$i18n.t('Orphaned files and attachments from deleted content')}</p>
                            <p>• {$i18n.t('Vector embeddings and collections for removed data')}</p>
                            <p>• {$i18n.t('Uploaded files that lost their database references')}</p>
                            <p>• {$i18n.t('Vector storage directories without corresponding data')}</p>
                          </div>
                        {:else if activeDetailsTab === 'imagesaudio'}
                          <div class="space-y-1">
                            <p><strong>{$i18n.t('Images & Audio Content Cleanup:')}</strong></p>
                            <p>• {$i18n.t('TBD - Image cleanup functionality')}</p>
                            <p>• {$i18n.t('TBD - Audio cleanup functionality')}</p>
                            <p>• {$i18n.t('TBD - Orphaned images and audio files')}</p>
                            <p>• {$i18n.t('TBD - Media processing cache cleanup')}</p>
                          </div>
                        {:else if activeDetailsTab === 'system'}
                          <div class="space-y-1">
                            <p><strong>{$i18n.t('Database & System Cleanup:')}</strong></p>
                            <p>• {$i18n.t('Removal of broken database references and stale entries')}</p>
                            <p>• {$i18n.t('Disk space reclamation by database cleanup')}</p>
                            <p>• {$i18n.t('Synchronization of database records with actual file storage')}</p>
                            <p>• {$i18n.t('Fix inconsistencies between storage systems')}</p>
                            <p>• {$i18n.t('Database performance optimization')}</p>
                          </div>
                        {/if}
                      </div>
                    </div>
                  {/if}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Performance Warning -->
        <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <p class="text-sm text-yellow-800 dark:text-yellow-200">
                {$i18n.t('Performance Warning: This operation may take a very long time to complete, especially if you have never cleaned your database before or if your instance stores large amounts of data. The process could take anywhere from seconds, to minutes, to half an hour and beyond depending on your data size.')}
              </p>
            </div>
          </div>
        </div>

        <!-- Settings Section with Tabs -->
        <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div class="flex items-center mb-3">
            <svg class="h-4 w-4 text-blue-600 dark:text-blue-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
            </svg>
            <h4 class="text-sm font-medium text-blue-800 dark:text-blue-200">
              {$i18n.t('Pruning Configuration')}
            </h4>
          </div>
          <p class="text-xs text-blue-700 dark:text-blue-300 mb-4">
            {$i18n.t('Configure what data should be cleaned up during the pruning process.')}
          </p>

          <!-- Settings Tab Navigation - ONLY CHATS AND WORKSPACE -->
          <div class="flex flex-wrap gap-1 mb-4 border-b border-blue-300 dark:border-blue-700">
            <button
              class="px-3 py-2 text-sm font-medium rounded-t transition-colors {activeSettingsTab === 'chats' ? 'bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200' : 'text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200'}"
              on:click={() => activeSettingsTab = 'chats'}
            >
              {$i18n.t('Chats')}
            </button>
            <button
              class="px-3 py-2 text-sm font-medium rounded-t transition-colors {activeSettingsTab === 'workspace' ? 'bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200' : 'text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200'}"
              on:click={() => activeSettingsTab = 'workspace'}
            >
              {$i18n.t('Workspace')}
            </button>
          </div>

          <!-- Settings Tab Content - ONLY CHATS AND WORKSPACE -->
          <div class="space-y-4">
            {#if activeSettingsTab === 'chats'}
              <!-- Age-Based Chat Deletion -->
              <div class="space-y-4">
                <div class="flex items-start py-2">
                  <div class="flex items-center">
                    <div class="mr-3">
                      <Switch bind:state={deleteChatsByAge} />
                    </div>
                    <div>
                      <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {$i18n.t('Delete chats by age')}
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {$i18n.t('Optionally remove old chats based on last update time')}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Chat Options (when enabled) -->
                {#if deleteChatsByAge}
                  <div class="ml-8 space-y-4 border-l-2 border-gray-200 dark:border-gray-700 pl-4">
                    <div class="space-y-2">
                      <label class="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {$i18n.t('Delete chats older than')}
                      </label>
                      <div class="flex items-center space-x-2">
                        <input
                          id="days"
                          type="number"
                          min="0"
                          bind:value={days}
                          class="w-20 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <span class="text-sm text-gray-700 dark:text-gray-300">{$i18n.t('days')}</span>
                      </div>
                      <p class="text-xs text-gray-500 dark:text-gray-400">
                        {$i18n.t('Set to 0 to delete all chats, or specify number of days')}
                      </p>
                    </div>
                    
                    <div class="flex items-start py-2">
                      <div class="flex items-center">
                        <div class="mr-3">
                          <Switch bind:state={exempt_archived_chats} />
                        </div>
                        <div>
                          <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {$i18n.t('Exempt archived chats')}
                          </div>
                          <div class="text-xs text-gray-500 dark:text-gray-400">
                            {$i18n.t('Keep archived chats even if they are old')}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div class="flex items-start py-2">
                      <div class="flex items-center">
                        <div class="mr-3">
                          <Switch bind:state={exempt_chats_in_folders} />
                        </div>
                        <div>
                          <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {$i18n.t('Exempt chats in folders')}
                          </div>
                          <div class="text-xs text-gray-500 dark:text-gray-400">
                            {$i18n.t('Keep chats that are organized in folders or pinned')}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                {/if}

                <!-- Orphaned Chat Deletion -->
                <div class="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <div class="flex items-start py-2">
                    <div class="flex items-center">
                      <div class="mr-3">
                        <Switch bind:state={delete_orphaned_chats} />
                      </div>
                      <div>
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {$i18n.t('Delete orphaned chats')}
                        </div>
                        <div class="text-xs text-gray-500 dark:text-gray-400">
                          {$i18n.t('Delete orphaned chats from deleted users')}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="flex items-start py-2">
                    <div class="flex items-center">
                      <div class="mr-3">
                        <Switch bind:state={delete_orphaned_folders} />
                      </div>
                      <div>
                        <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {$i18n.t('Delete orphaned folders')}
                        </div>
                        <div class="text-xs text-gray-500 dark:text-gray-400">
                          {$i18n.t('Delete orphaned folders from deleted users')}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

            {:else if activeSettingsTab === 'workspace'}
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <!-- Knowledge Bases -->
                <div class="flex items-start py-2">
                  <div class="flex items-center">
                    <div class="mr-3">
                      <Switch bind:state={delete_orphaned_knowledge_bases} />
                    </div>
                    <div>
                      <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {$i18n.t('Delete orphaned knowledge bases')}
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {$i18n.t('Delete orphaned knowledge bases from deleted users')}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Tools -->
                <div class="flex items-start py-2">
                  <div class="flex items-center">
                    <div class="mr-3">
                      <Switch bind:state={delete_orphaned_tools} />
                    </div>
                    <div>
                      <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {$i18n.t('Delete orphaned tools')}
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {$i18n.t('Delete orphaned custom tools from deleted users')}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Functions -->
                <div class="flex items-start py-2">
                  <div class="flex items-center">
                    <div class="mr-3">
                      <Switch bind:state={delete_orphaned_functions} />
                    </div>
                    <div>
                      <div class="flex items-center text-sm font-medium text-gray-900 dark:text-gray-100">
                        <span>{$i18n.t('Delete orphaned functions')}</span>
                        <div class="relative group ml-2">
                          <svg class="h-3 w-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                          </svg>
                          <div class="absolute left-1/2 transform -translate-x-1/2 bottom-full mb-2 w-48 px-3 py-2 text-xs text-white bg-gray-900 dark:bg-gray-700 rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10">
                            <div class="font-medium mb-1">{$i18n.t('Admin panel functions - all functions, including:')}</div>
                            <div class="space-y-0.5">
                              <div>• {$i18n.t('Actions')}</div>
                              <div>• {$i18n.t('Pipes')}</div>
                              <div>• {$i18n.t('Filters')}</div>
                            </div>
                            <div class="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900 dark:border-t-gray-700"></div>
                          </div>
                        </div>
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {$i18n.t('Delete orphaned custom functions from deleted users')}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Prompts -->
                <div class="flex items-start py-2">
                  <div class="flex items-center">
                    <div class="mr-3">
                      <Switch bind:state={delete_orphaned_prompts} />
                    </div>
                    <div>
                      <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {$i18n.t('Delete orphaned prompts')}
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {$i18n.t('Delete orphaned custom prompts from deleted users')}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Models -->
                <div class="flex items-start py-2">
                  <div class="flex items-center">
                    <div class="mr-3">
                      <Switch bind:state={delete_orphaned_models} />
                    </div>
                    <div>
                      <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {$i18n.t('Delete orphaned models')}
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {$i18n.t('Delete orphaned custom models from deleted users')}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Notes -->
                <div class="flex items-start py-2">
                  <div class="flex items-center">
                    <div class="mr-3">
                      <Switch bind:state={delete_orphaned_notes} />
                    </div>
                    <div>
                      <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {$i18n.t('Delete orphaned notes')}
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {$i18n.t('Delete orphaned notes from deleted users')}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            {/if}
          </div>
        </div>

        <!-- API Call Preview Section -->
        <div class="bg-gray-50 dark:bg-gray-900/20 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3 flex-1">
              <h3 class="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">
                {$i18n.t('API Automation Helper')}
              </h3>
              
              <button
                class="flex items-center text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 focus:outline-none mb-3"
                on:click={() => showApiPreview = !showApiPreview}
              >
                <svg 
                  class="w-3 h-3 mr-1 transition-transform duration-200 {showApiPreview ? 'rotate-90' : ''}" 
                  fill="currentColor" 
                  viewBox="0 0 20 20"
                >
                  <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                </svg>
                {showApiPreview ? $i18n.t('Hide API call') : $i18n.t('Show API call')}
              </button>

              {#if showApiPreview}
                <div class="space-y-2">
                  <p class="text-sm text-gray-700 dark:text-gray-300 mb-3">
                    {$i18n.t('Use this API call configuration to automate pruning operations in your own maintenance scripts.')}
                  </p>
                  <div class="relative">
                    <textarea
                      readonly
                      value={apiCallPreview}
                      class="w-full h-40 px-3 py-2 text-xs font-mono bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 resize-none focus:ring-2 focus:ring-gray-500 focus:border-gray-500"
                      on:focus={(e) => e.target.select()}
                    ></textarea>
                    <button
                      class="absolute top-2 right-2 px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-2 focus:ring-gray-500"
                      on:click={copyApiCall}
                      title={$i18n.t('Copy to clipboard')}
                    >
                      <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z"></path>
                        <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z"></path>
                      </svg>
                    </button>
                  </div>
                </div>
              {/if}
            </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="mt-6 flex justify-end gap-3">
        <button
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700 transition-colors"
          on:click={() => (show = false)}
        >
          {$i18n.t('Cancel')}
        </button>
        <button
          class="px-4 py-2 text-sm font-medium text-white bg-yellow-600 border border-transparent rounded-lg hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 transition-colors"
          on:click={confirm}
        >
          {$i18n.t('Prune Data')}
        </button>
      </div>
    </div>
  </div>
</Modal>
