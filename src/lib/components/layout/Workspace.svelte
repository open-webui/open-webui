<!-- Workspace Button -->
{#if $user?.role === 'admin'}
<div class="px-2.5 flex justify-center text-gray-800 dark:text-gray-200">
    <a
        class="flex-grow flex space-x-3 rounded-xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
        href="/workspace"
        on:click={() => {
            selectedChatId = null;
            chatId.set('');

            if ($mobile) {
                showSidebar.set(false);
            }
        }}
        draggable="false"
    >
        <div class="self-center">
            <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="2"
                stroke="currentColor"
                class="size-[1.1rem]"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 0 0 2.25-2.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v2.25A2.25 2.25 0 0 0 6 10.5Zm0 9.75h2.25A2.25 2.25 0 0 0 10.5 18v-2.25a2.25 2.25 0 0 0-2.25-2.25H6a2.25 2.25 0 0 0-2.25 2.25V18A2.25 2.25 0 0 0 6 20.25Zm9.75-9.75H18a2.25 2.25 0 0 0 2.25-2.25V6A2.25 2.25 0 0 0 18 3.75h-2.25A2.25 2.25 0 0 0 13.5 6v2.25a2.25 2.25 0 0 0 2.25 2.25Z"
                />
            </svg>
        </div>

        <div class="flex self-center">
            <div class=" self-center font-medium text-sm font-primary">{$i18n.t('Workspace')}</div>
        </div>
    </a>
</div>
{/if}