<script lang="ts">
	import { getContext, createEventDispatcher, onMount } from 'svelte';
	import { createNewChannel, deleteChannelById } from '$lib/apis/channels';

	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	const i18n = getContext('i18n');

	export let show = false;
	export let onSubmit: Function = () => {};
	export let onUpdate: Function = () => {};

	export let channel = null;
	export let edit = false;

	let name = '';
	let accessControl = null;

	let loading = false;

	$: if (name) {
		name = name.replace(/\s/g, '-').toLocaleLowerCase();
	}

	const submitHandler = async () => {
		loading = true;
		await onSubmit({
			name: name.replace(/\s/g, '-'),
			access_control: accessControl
		});
		show = false;
		loading = false;
	};

	const init = () => {
		name = channel.name;
		accessControl = channel.access_control;
	};

	$: if (channel) {
		init();
	}

	let showDeleteConfirmDialog = false;

	const deleteHandler = async () => {
		showDeleteConfirmDialog = false;

		const res = await deleteChannelById(localStorage.token, channel.id).catch((error) => {
			toast.error(error.message);
		});

		if (res) {
			toast.success('Channel deleted successfully');
			onUpdate();

			if ($page.url.pathname === `/channels/${channel.id}`) {
				goto('/');
			}
		}

		show = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class=" text-lg font-medium self-center">
				{#if edit}
					{$i18n.t('Edit Channel')}
				{:else}
					{$i18n.t('Create Channel')}
				{/if}
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
						fill-rule="evenodd"
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						clip-rule="evenodd"
					/>
				</svg>
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
					<div class="flex flex-col w-full mt-2">
						<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Channel Name')}</div>

						<div class="flex-1">
							<input
								class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none"
								type="text"
								bind:value={name}
								placeholder={$i18n.t('new-channel')}
								autocomplete="off"
							/>
						</div>
					</div>

					<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

					<div class="my-2 -mx-2">
						<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
							<AccessControl bind:accessControl />
						</div>
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						{#if edit}
							<button
								class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-black/90 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{#if edit}
								{$i18n.t('Update')}
							{:else}
								{$i18n.t('Create')}
							{/if}

							{#if loading}
								<div class="ml-2 self-center">
									<svg
										class=" w-4 h-4"
										viewBox="0 0 24 24"
										fill="currentColor"
										xmlns="http://www.w3.org/2000/svg"
										><style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}
											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style><path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/><path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/></svg
									>
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<DeleteConfirmDialog
	bind:show={showDeleteConfirmDialog}
	message={$i18n.t('Are you sure you want to delete this channel?')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={() => {
		deleteHandler();
	}}
/>
