<!-- Company custom: Team Workspaces V1 -->
<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';

	import { mobile, showSidebar, activeWorkspaceId } from '$lib/stores';
	import { getWorkspaceChats } from '$lib/apis/workspaces';

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Users from '$lib/components/icons/Users.svelte';

	const i18n = getContext('i18n');

	export let workspace: any;
	export let onManage: () => void = () => {};

	export let className = '';

	let open = false;
	let chats: any[] = [];

	const openWorkspace = async () => {
		open = !open;
		activeWorkspaceId.set(open ? workspace.id : null);
		if (open) await refreshChats();
	};

	const refreshChats = async () => {
		try {
			const result = await getWorkspaceChats(localStorage.token, workspace.id);
			chats = result ?? [];
		} catch (e) {
			toast.error(`${e}`);
		}
	};
</script>

<div class="w-full {className}">
	<!-- Workspace header row -->
	<div
		class="group flex items-center justify-between w-full rounded-xl px-2 py-1 cursor-pointer
		       hover:bg-gray-100 dark:hover:bg-gray-900
		       {$activeWorkspaceId === workspace.id ? 'bg-gray-100 dark:bg-gray-900' : ''}
		       dark:text-gray-400 text-gray-600 select-none"
		role="button"
		tabindex="0"
		on:click={openWorkspace}
		on:keydown={(e) => e.key === 'Enter' && openWorkspace()}
	>
		<div class="flex items-center gap-1.5 overflow-hidden">
			<!-- Workspace icon -->
			<div class="size-4 flex items-center justify-center ml-0.5 shrink-0">
				<Users className="size-3.5" strokeWidth="2" />
			</div>

			<span class="text-sm line-clamp-1 flex-1">{workspace.name}</span>
		</div>

		<div class="flex items-center gap-1 shrink-0">
			<!-- Manage button (hover only) -->
			<button
				type="button"
				class="p-0.5 dark:hover:bg-gray-850 rounded-lg touch-auto invisible group-hover:visible"
				title={$i18n.t('Manage workspace')}
				on:click|stopPropagation={onManage}
			>
				<Cog6 className="size-3.5" />
			</button>

			<!-- Chevron -->
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="size-3.5 transition-transform duration-150 {open ? 'rotate-90' : ''}"
			>
				<path
					fill-rule="evenodd"
					d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
	</div>

	<!-- Chat list (shown when workspace is open) -->
	{#if open}
		<div class="ml-2 mt-0.5 flex flex-col gap-0.5">
			{#if chats.length === 0}
				<div class="px-3 py-1 text-xs text-gray-400 dark:text-gray-600 italic">
					{$i18n.t('No chats yet')}
				</div>
			{:else}
				{#each chats as chat (chat.id)}
					<a
						href="/c/{chat.id}"
						draggable="false"
						class="group/chat flex items-center gap-1.5 w-full rounded-xl px-2 py-1 text-sm
						       hover:bg-gray-100 dark:hover:bg-gray-900
						       {$page.url.pathname === `/c/${chat.id}`
							? 'bg-gray-100 dark:bg-gray-900 font-medium dark:text-white text-black'
							: 'dark:text-gray-400 text-gray-600'}
						       line-clamp-1 cursor-pointer select-none"
						on:click={() => {
							if ($mobile) showSidebar.set(false);
						}}
					>
						<span class="line-clamp-1 flex-1">{chat.title}</span>
					</a>
				{/each}
			{/if}
		</div>
	{/if}
</div>
