<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { user, showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');

	export let prompt = null;

	let loading = true;
	let error = null;

	let title = '';
	let command = '';
	let content = '';

	const toggleSidebar = () => {
		showSidebar.set(!$showSidebar);
	};

	onMount(async () => {
		if (prompt) {
			title = prompt.title;
			await tick();

			command = prompt.command.at(0) === '/' ? prompt.command.slice(1) : prompt.command;
			content = prompt.content;
			loading = false;
		} else {
			error = $i18n.t('Prompt not found');
			loading = false;
		}
	});
</script>

<div class="w-full max-h-full">
	<div class="flex-1 flex flex-col overflow-hidden">
		<div class="flex-1 overflow-y-auto">
			{#if loading}
				<div class="flex justify-center items-center h-64">
					<div class="loader">Loading...</div>
				</div>
			{:else if error}
				<div class="flex justify-center items-center h-64">
					<div class="text-red-500">{error}</div>
				</div>
			{:else}
				<div class="flex flex-col max-w-lg mx-auto mt-10 mb-10">
					<div class="text-2xl font-medium font-primary mb-4 dark:text-gray-300">
						{$i18n.t('View prompt')}
					</div>

					<div class="w-full flex flex-col gap-2.5">
						<div class="w-full">
							<div class="text-sm mb-2 dark:text-gray-300">{$i18n.t('Title')}</div>
							<input
								class="w-full mt-1 px-4 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 dark:text-gray-300"
								type="text"
								value={title}
								readonly
							/>
						</div>

						<div class="w-full">
							<div class="text-sm mb-2 dark:text-gray-300">{$i18n.t('Command')}</div>
							<input
								class="w-full mt-1 px-4 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 dark:text-gray-300"
								type="text"
								value={command}
								readonly
							/>
						</div>

						<div>
							<div class="text-sm mb-2 dark:text-gray-300">{$i18n.t('Prompt Content')}</div>
							<textarea
								class="w-full mt-1 px-4 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 dark:text-gray-300"
								rows="4"
								readonly
								value={content}
							></textarea>
						</div>
					</div>
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
			{/if}
		</div>
	</div>
</div>
