<script lang="ts">
	import { getContext, createEventDispatcher, onMount, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import { updateUserStatus } from '$lib/apis/users';
	import { settings, user } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import EmojiPicker from '$lib/components/common/EmojiPicker.svelte';
	import FaceSmile from '$lib/components/icons/FaceSmile.svelte';
	import Emoji from '$lib/components/common/Emoji.svelte';

	export let show = false;
	export let onSave: Function = () => {};

	let emoji = '';
	let message = '';

	let loading = false;

	const submitHandler = async () => {
		loading = true;
		const res = await updateUserStatus(localStorage.token, {
			status_emoji: emoji,
			status_message: message
		}).catch((error) => {
			toast.error(`${error}`);
			loading = false;
			return null;
		});

		if (res) {
			toast.success($i18n.t('Status updated successfully'));
			onSave();
		} else {
			toast.error($i18n.t('Failed to update status'));
		}

		show = false;
		loading = false;
	};

	$: if (show) {
		init();
	} else {
		resetHandler();
	}

	const init = async () => {
		emoji = $user?.status_emoji || '';
		message = $user?.status_message || '';

		await tick();
		const input = document.getElementById('status-message') as HTMLInputElement;
		if (input) {
			input.focus();
			input.select();
		}
	};

	const resetHandler = () => {
		emoji = '';
		message = '';
		loading = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class=" text-lg font-medium self-center">
				{$i18n.t('Set your status')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div>
						<div class="text-xs text-gray-500 mb-1.5">
							{$i18n.t('Status')}
						</div>

						<div
							class="flex items-center px-2.5 py-2 gap-3 border border-gray-100/50 dark:border-gray-850/50 rounded-xl"
						>
							<EmojiPicker
								onClose={() => {}}
								onSubmit={(name) => {
									console.log(name);
									emoji = name;
								}}
							>
								<div class=" flex items-center">
									{#if emoji}
										<Emoji shortCode={emoji} />
									{:else}
										<FaceSmile />
									{/if}
								</div>
							</EmojiPicker>

							<input
								id="status-message"
								type="text"
								bind:value={message}
								class={`w-full flex-1 text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
								placeholder={$i18n.t("What's on your mind?")}
								autocomplete="off"
								required
							/>

							<button
								type="button"
								on:click={() => {
									emoji = '';
									message = '';
								}}
							>
								<XMark />
							</button>
						</div>
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
