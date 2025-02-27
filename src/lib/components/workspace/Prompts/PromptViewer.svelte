<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user, showSidebar, mobile } from '$lib/stores';
	import { getPromptByCommand } from '$lib/apis/prompts';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');

	export let command: string;
	let prompt = null;
	let loading = true;
	let error = null;

	const toggleSidebar = () => {
		showSidebar.set(!$showSidebar);
	};

	onMount(async () => {
		try {
			// Remove any leading slash from the command
			const sanitizedCommand = command?.replace(/^\//, '');
			if (!sanitizedCommand) {
				throw new Error('Invalid command');
			}

			prompt = await getPromptByCommand(localStorage.token, sanitizedCommand);
		} catch (err) {
			console.error('Error loading prompt:', err);
			error = err.message || 'Failed to load prompt';
		} finally {
			loading = false;
		}
		// Initialize sidebar state but don't force it based on mobile/desktop
		showSidebar.set(localStorage.sidebar === 'true');
	});
</script>

<div class="flex h-screen w-full overflow-hidden bg-white dark:bg-gray-900">
	<div class="flex w-full">
		<Sidebar />
		<div class="flex-1 flex flex-col overflow-hidden">
			<nav class="w-full px-2.5 pt-1 backdrop-blur-xl drag-region">
				<div class="flex items-center gap-1">
					<div class="{!$showSidebar ? '' : 'md:hidden'} self-center flex flex-none items-center">
						<button
							id="sidebar-toggle-button"
							class="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							aria-label="Toggle Sidebar"
							on:click={toggleSidebar}
						>
							<div class="m-auto self-center">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									class="size-5"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12"
									/>
								</svg>
							</div>
						</button>
					</div>
					<div class="">
						<div
							class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
						>
							{#if $user?.role === 'admin' || $user?.permissions?.workspace?.prompts}
								<a
									class="min-w-fit rounded-full p-1.5 transition dark:text-gray-300"
									href="/workspace/prompts"
								>
									{$i18n.t('Prompts')}
								</a>
							{/if}
						</div>
					</div>
				</div>
			</nav>

			<div class="flex-1 overflow-y-auto">
				{#if loading}
					<div class="flex justify-center items-center h-64">
						<div class="loader">Loading...</div>
					</div>
				{:else if error}
					<div class="flex justify-center items-center h-64">
						<div class="text-red-500">{error}</div>
					</div>
				{:else if prompt}
					<div class="flex flex-col max-w-lg mx-auto mt-10 mb-10">
						<div class="text-2xl font-medium font-primary mb-4 dark:text-gray-300">
							{$i18n.t('View prompt')}
						</div>

						<div class="w-full flex flex-col gap-2.5">
							<div class="w-full">
								<div class="text-sm mb-2 dark:text-gray-300">{$i18n.t('Title')}</div>
								<div
									class="w-full mt-1 px-4 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 dark:text-gray-300"
								>
									{prompt.title}
								</div>
							</div>

							<div class="w-full">
								<div class="text-sm mb-2 dark:text-gray-300">{$i18n.t('Command')}</div>
								<div
									class="w-full mt-1 px-4 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 dark:text-gray-300"
								>
									{prompt.command}
								</div>
							</div>

							<div>
								<div class="text-sm mb-2 dark:text-gray-300">{$i18n.t('Prompt Content')}</div>
								<div
									class="w-full mt-1 px-4 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 dark:text-gray-300 whitespace-pre-wrap"
								>
									{prompt.content}
								</div>
							</div>
						</div>
						<!-- Add close button here -->
						<div class="flex justify-end mt-2">
							<button
								class="text-sm px-4 py-2 transition rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white"
								on:click={() => goto('/workspace/prompts')}
							>
								<div class="self-center font-medium">
									{$i18n.t('Close')}
								</div>
							</button>
						</div>
					</div>
				{:else}
					<div class="flex justify-center items-center h-64">
						<div class="text-gray-500">{$i18n.t('Prompt not found')}</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
