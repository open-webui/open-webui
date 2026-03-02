<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	const dispatch = createEventDispatcher();

	let projectName = '';
	let selectedCategory = '';

	const categories = [
		{ id: 'investing', name: 'Investing', icon: '💰', color: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-green-300 dark:border-green-700' },
		{ id: 'homework', name: 'Homework', icon: '🎓', color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border-blue-300 dark:border-blue-700' },
		{ id: 'writing', name: 'Writing', icon: '✍️', color: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 border-purple-300 dark:border-purple-700' },
		{ id: 'travel', name: 'Travel', icon: '✈️', color: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 border-yellow-300 dark:border-yellow-700' }
	];

	const handleSubmit = () => {
		if (!projectName.trim()) {
			toast.error($i18n.t('Please enter a project name'));
			return;
		}

		dispatch('create', {
			name: projectName.trim(),
			category: selectedCategory
		});

		// Reset form
		projectName = '';
		selectedCategory = '';
		show = false;
	};

	const handleClose = () => {
		projectName = '';
		selectedCategory = '';
		show = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<!-- Header -->
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class="text-lg font-medium self-center">
				{$i18n.t('Create Project')}
			</div>
			<button
				class="self-center"
				on:click={handleClose}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						fill-rule="evenodd"
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</div>

		<!-- Content -->
		<div class="flex flex-col w-full px-5 pb-4 dark:text-gray-200">
			<form
				class="flex flex-col w-full"
				on:submit|preventDefault={handleSubmit}
			>
				<!-- Project Name Input -->
				<div class="flex flex-col w-full mt-2">
					<div class="mb-1 text-xs text-gray-500">{$i18n.t('Project Name')}</div>
					<div class="flex-1">
						<input
							class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
							type="text"
							bind:value={projectName}
							placeholder={$i18n.t('Copenhagen Trip')}
							autocomplete="off"
							autofocus
						/>
					</div>
				</div>

				<hr class="border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

				<!-- Category Selection -->
				<!-- <div class="my-2">
					<div class="mb-2 text-xs text-gray-500">{$i18n.t('Category')} ({$i18n.t('Optional')})</div>
					<div class="flex flex-wrap gap-2">
						{#each categories as category}
							<button
								type="button"
								class="category-button px-3 py-2 rounded-lg border-2 transition-all duration-200 flex items-center gap-2 text-sm {selectedCategory ===
								category.id
									? `${category.color} font-medium`
									: 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'}"
								on:click={() => {
									selectedCategory = selectedCategory === category.id ? '' : category.id;
								}}
							>
								<span>{category.icon}</span>
								<span>{$i18n.t(category.name)}</span>
							</button>
						{/each}
					</div>
				</div>

				<hr class="border-gray-100 dark:border-gray-700/10 my-2.5 w-full" /> -->

				<!-- Info Banner -->
				<div class="my-2 p-3 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 rounded-lg">
					<div class="flex gap-2.5">
						<div class="flex-shrink-0 mt-0.5">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="w-4 h-4 text-blue-600 dark:text-blue-400"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
								/>
							</svg>
						</div>
						<div class="flex-1">
							<p class="text-xs text-blue-900 dark:text-blue-200 leading-relaxed">
								{$i18n.t('Projects keep chats, files, and custom instructions in one place. Use them for ongoing work, or just to keep things tidy.')}
							</p>
						</div>
					</div>
				</div>

				<!-- Submit Button -->
				<div class="flex justify-end pt-3 text-sm font-medium">
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
						type="submit"
						disabled={!projectName.trim()}
					>
						{$i18n.t('Create')}
					</button>
				</div>
			</form>
		</div>
	</div>
</Modal>

<style>
	.category-button {
		user-select: none;
		-webkit-user-select: none;
	}

	.category-button:active {
		transform: scale(0.98);
	}
</style>