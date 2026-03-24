<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';

	const i18n: any = getContext('i18n');

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


<Modal
	size="sm"
	bind:show
	backdropClassName="bg-black/20 backdrop-blur-[1px] dark:bg-black/35"
	className="rounded-3xl border border-gray-200 bg-white/96 shadow-2xl dark:border-gray-800 dark:bg-gray-900/96"
>
	<div>
		<!-- Header -->
		<div class="flex items-center justify-between px-6 pt-5 pb-2 dark:text-gray-300">
			<div class="text-xl font-semibold self-center text-gray-900 dark:text-gray-100 tracking-tight">
				{$i18n.t('Create Project')}
			</div>
			<button
				class="self-center rounded-full p-1.5 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100"
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
		<div class="flex flex-col w-full px-6 pb-5 dark:text-gray-200">
			<form
				class="flex flex-col w-full"
				on:submit|preventDefault={handleSubmit}
			>
				<!-- Project Name Input -->
				<div class="flex flex-col w-full mt-1">
					<div class="mb-1.5 text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">{$i18n.t('Project Name')}</div>
					<div class="flex-1">
						<input
							class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 outline-none transition focus:border-orange-300 focus:ring-2 focus:ring-orange-100 dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:border-orange-500/60 dark:focus:ring-orange-500/20"
							type="text"
							bind:value={projectName}
							placeholder={$i18n.t('Create your new project')}
							autocomplete="off"
						/>
					</div>
				</div>

				<hr class="my-3.5 w-full border-gray-100 dark:border-gray-700/40" />

				<div class="rounded-xl border border-blue-200 bg-gradient-to-b from-blue-50 to-blue-100/60 p-3 dark:border-blue-900/70 dark:from-blue-950/40 dark:to-blue-950/20">
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
							<p class="text-xs leading-relaxed text-blue-900 dark:text-blue-200">
								{$i18n.t('Projects keep chats, files, and custom instructions in one place. Use them for ongoing work, or just to keep things tidy.')}
							</p>
						</div>
					</div>
				</div>

				<!-- Submit Button -->
				<div class="flex justify-end pt-4 text-sm font-medium">
					<button
						class="rounded-full bg-gray-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
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

