<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';

	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Modal from '$lib/components/common/Modal.svelte';
	export let show = false;

	let name = '';
	let content = '';
</script>

<Modal size="md" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4">
			<div class=" text-lg font-medium self-center">{$i18n.t('Add Content')}</div>
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
		<div class="flex flex-col md:flex-row w-full px-5 py-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						if (name.trim() === '' || content.trim() === '') {
							toast.error($i18n.t('Please fill in all fields.'));
							name = '';
							content = '';
							return;
						}

						dispatch('submit', {
							name,
							content
						});
						show = false;
						name = '';
						content = '';
					}}
				>
					<div class="mb-3 w-full">
						<div class="w-full flex flex-col gap-2.5">
							<div class="w-full">
								<div class=" text-sm mb-2">Title</div>

								<div class="w-full mt-1">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-white dark:text-gray-300 dark:bg-gray-850 outline-none"
										type="text"
										bind:value={name}
										placeholder={`Name your content`}
										required
									/>
								</div>
							</div>

							<div>
								<div class="text-sm mb-2">Content</div>

								<div class=" w-full mt-1">
									<textarea
										class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-whites dark:text-gray-300 dark:bg-gray-850 outline-none"
										rows="10"
										bind:value={content}
										placeholder={`Write your content here`}
										required
									/>
								</div>
							</div>
						</div>
					</div>

					<div class="flex justify-end text-sm font-medium">
						<button
							class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
							type="submit"
						>
							{$i18n.t('Add Content')}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
