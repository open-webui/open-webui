<script lang="ts">
  import { createEventDispatcher, getContext, onMount } from 'svelte';
  import { DropdownMenu } from 'bits-ui';
  import { showSettings, activeUserIds, USAGE_POOL, mobile, showSidebar } from '$lib/stores';
  import { fade } from 'svelte/transition';
  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import { userSignOut } from '$lib/apis/auths';
  import UpdatePlanModal from '$lib/components/UpdatePlanModal.svelte'; // Импортируем модальное окно

  const i18n = getContext('i18n');

  export let show = false;
  export let role = '';
  export let className = 'max-w-[240px]';

  const dispatch = createEventDispatcher();
  
  // Состояние для открытия модального окна
  let showUpdatePlanModal = false;
</script>

<DropdownMenu.Root
  bind:open={show}
  onOpenChange={(state) => {
    dispatch('change', state);
  }}
>
  <DropdownMenu.Trigger>
    <slot />
  </DropdownMenu.Trigger>

  <slot name="content">
    <DropdownMenu.Content
      class="w-full {className} text-sm rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg font-primary"
      sideOffset={8}
      side="bottom"
      align="start"
      transition={(e) => fade(e, { duration: 100 })}
    >
      <!-- Новый пункт меню: Обновить план -->
      <button
        class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
        on:click={() => showUpdatePlanModal = true} 
      >
        <div class="self-center mr-3">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
        </div>
        <div class="self-center truncate">{$i18n.t('Update Plan')}</div>
      </button>

      <!-- Другие элементы меню -->

      <button
        class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
        on:click={async () => {
          await showSettings.set(true);
          show = false;

          if ($mobile) {
            showSidebar.set(false);
          }
        }}
      >
        <div class=" self-center mr-3">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <div class=" self-center truncate">{$i18n.t('Settings')}</div>
      </button>

      <button
        class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
        on:click={() => {
          dispatch('show', 'archived-chat');
          show = false;

          if ($mobile) {
            showSidebar.set(false);
          }
        }}
      >
        <div class=" self-center mr-3">
          <ArchiveBox className="size-5" strokeWidth="1.5" />
        </div>
        <div class=" self-center truncate">{$i18n.t('Archived Chats')}</div>
      </button>

      {#if role === 'admin'}
        <a
          class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
          href="/playground"
          on:click={() => {
            show = false;

            if ($mobile) {
              showSidebar.set(false);
            }
          }}
        >
          <div class=" self-center mr-3">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
              class="size-5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M14.25 9.75 16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z"
              />
            </svg>
          </div>
          <div class=" self-center truncate">{$i18n.t('Playground')}</div>
        </a>

        <a
          class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
          href="/admin"
          on:click={() => {
            show = false;

            if ($mobile) {
              showSidebar.set(false);
            }
          }}
        >
          <div class=" self-center mr-3">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
              class="w-5 h-5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </div>
          <div class=" self-center truncate">{$i18n.t('Admin Panel')}</div>
        </a>
      {/if}

      <hr class=" border-gray-50 dark:border-gray-850 my-1 p-0" />

      <button
        class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
        on:click={userSignOut}
      >
        <div class=" self-center mr-3">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
            class="w-5 h-5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M15 10.5h4.5m0 0H15m4.5 0l-3-3m3 3l-3 3m-6 4.5h-6a2.25 2.25 0 0 1-2.25-2.25V6A2.25 2.25 0 0 1 6 3.75h6a2.25 2.25 0 0 1 2.25 2.25v12a2.25 2.25 0 0 1-2.25 2.25z"
            />
          </svg>
        </div>
        <div class=" self-center truncate">{$i18n.t('Sign out')}</div>
      </button>
    </DropdownMenu.Content>
  </slot>
</DropdownMenu.Root>

<!-- Модальное окно -->
{#if showUpdatePlanModal}
  <UpdatePlanModal {showUpdatePlanModal} on:close={() => showUpdatePlanModal = false} />
{/if}
