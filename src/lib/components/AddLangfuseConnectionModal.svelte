<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Modal from '$lib/components/common/Modal.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { verifyLangfuseConnection } from '$lib/apis/configs';

	type LangfuseConnectionForm = {
		id?: string;
		name?: string;
		url?: string;
		public_key?: string;
		secret_key?: string;
		secret_key_set?: boolean;
		enabled?: boolean;
	};

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let show = false;
	export let edit = false;
	export let connection: LangfuseConnectionForm | null = null;

	export let onSubmit: (connection: LangfuseConnectionForm) => void = () => {};
	export let onDelete: () => void = () => {};

	let id = '';
	let name = '';
	let url = '';
	let publicKey = '';
	let secretKey = '';
	let secretKeySet = false;
	let enabled = true;
	let verifying = false;
	let showDeleteConfirmDialog = false;

	const inputClass =
		'rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

	const init = () => {
		if (connection) {
			id = connection?.id ?? '';
			name = connection?.name ?? '';
			url = connection?.url ?? '';
			publicKey = connection?.public_key ?? '';
			secretKey = connection?.secret_key ?? '';
			secretKeySet = connection?.secret_key_set ?? Boolean(connection?.secret_key);
			enabled = connection?.enabled ?? true;
		} else {
			id = '';
			name = '';
			url = '';
			publicKey = '';
			secretKey = '';
			secretKeySet = false;
			enabled = true;
		}
	};

	$: if (show) {
		init();
	}

	const verifyHandler = async () => {
		const baseUrl = url.replace(/\/$/, '');
		if (!baseUrl) {
			toast.error($i18n.t('Please enter a valid URL'));
			return;
		}

		verifying = true;
		try {
			const result = await verifyLangfuseConnection(localStorage.token, {
				id: id || undefined,
				url: baseUrl,
				public_key: publicKey.trim(),
				secret_key: secretKey.trim()
			});

			if (result?.status) {
				toast.success($i18n.t('Server connection verified'));
			} else {
				toast.error($i18n.t('Server connection failed'));
			}
		} catch {
			toast.error($i18n.t('Server connection failed'));
		} finally {
			verifying = false;
		}
	};

	const submitHandler = () => {
		const baseUrl = url.replace(/\/$/, '');
		if (!baseUrl) {
			toast.error($i18n.t('Please enter a valid URL'));
			return;
		}

		if (!publicKey.trim()) {
			toast.error($i18n.t('Public key is required'));
			return;
		}

		if (!edit && !secretKey.trim()) {
			toast.error($i18n.t('Secret key is required'));
			return;
		}

		onSubmit({
			id: id.trim() || crypto.randomUUID(),
			name: name.trim(),
			url: baseUrl,
			public_key: publicKey.trim(),
			secret_key: secretKey.trim(),
			secret_key_set: secretKeySet || Boolean(secretKey.trim()),
			enabled
		});
		show = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-100 px-4 pt-3 pb-1">
			<h1 class="text-sm font-medium self-center">
				{#if edit}
					{$i18n.t('Edit Langfuse Connection')}
				{:else}
					{$i18n.t('Add Langfuse Connection')}
				{/if}
			</h1>

			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div class="flex flex-col w-full px-4 pb-4 dark:text-gray-200">
			<form class="flex flex-col w-full" on:submit|preventDefault={submitHandler}>
				<div class="px-1">
					<div class="flex gap-2">
						<div class="flex flex-col flex-1">
							<label for="langfuse-name" class="mb-0.5 text-xs text-gray-500">
								{$i18n.t('Name')}
							</label>
							<input
								id="langfuse-name"
								class={`w-full text-sm ${inputClass}`}
								type="text"
								bind:value={name}
								placeholder={$i18n.t('Production Langfuse')}
								autocomplete="off"
							/>
						</div>

						<div class="flex flex-col flex-1">
							<label for="langfuse-id" class="mb-0.5 text-xs text-gray-500">
								{$i18n.t('ID')}
								<span class="opacity-50">({$i18n.t('optional')})</span>
							</label>
							<input
								id="langfuse-id"
								class={`w-full text-sm font-mono ${inputClass}`}
								type="text"
								bind:value={id}
								placeholder="auto"
								autocomplete="off"
							/>
						</div>
					</div>

					<div class="mt-2 flex gap-2">
						<div class="flex w-full flex-col">
							<label for="langfuse-url" class="mb-0.5 text-xs text-gray-500">
								{$i18n.t('URL')}
							</label>
							<input
								id="langfuse-url"
								class={`w-full text-sm ${inputClass}`}
								type="text"
								bind:value={url}
								placeholder="https://cloud.langfuse.com"
								required
								autocomplete="off"
							/>
						</div>

						<Tooltip content={$i18n.t('Verify Connection')} className="self-end -mb-1">
							<button
								class="self-center rounded-lg bg-transparent p-1 transition hover:bg-gray-50/70 dark:hover:bg-gray-850/50"
								on:click={verifyHandler}
								type="button"
								disabled={verifying}
								aria-label={$i18n.t('Verify Connection')}
							>
								{#if verifying}
									<svg
										class="h-4 w-4 animate-spin"
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
									>
										<circle
											class="opacity-25"
											cx="12"
											cy="12"
											r="10"
											stroke="currentColor"
											stroke-width="4"
										></circle>
										<path
											class="opacity-75"
											fill="currentColor"
											d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
										></path>
									</svg>
								{:else}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										aria-hidden="true"
										class="h-4 w-4"
									>
										<path
											fill-rule="evenodd"
											d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
											clip-rule="evenodd"
										/>
									</svg>
								{/if}
							</button>
						</Tooltip>
					</div>

					<div class="mt-2 flex flex-col">
						<label for="langfuse-public-key" class="mb-0.5 text-xs text-gray-500">
							{$i18n.t('Public Key')}
						</label>
						<input
							id="langfuse-public-key"
							class={`w-full text-sm font-mono ${inputClass}`}
							type="text"
							bind:value={publicKey}
							placeholder="pk-lf-..."
							autocomplete="off"
							required
						/>
					</div>

					<div class="mt-2 flex flex-col">
						<div class="mb-0.5 text-xs text-gray-500">
							{$i18n.t('Secret Key')}
							{#if edit && secretKeySet && !secretKey}
								<span class="opacity-50">({$i18n.t('unchanged if empty')})</span>
							{/if}
						</div>
						<SensitiveInput
							bind:value={secretKey}
							placeholder={edit && secretKeySet ? '••••••••' : $i18n.t('sk-lf-...')}
							required={!edit}
						/>
					</div>

					<div class="mt-3 flex items-center justify-between text-sm font-normal">
						<div>
							{#if edit}
								<button
									class="px-1 py-1.5 text-sm font-normal text-gray-500 transition hover:text-gray-700 hover:underline dark:text-gray-400 dark:hover:text-gray-200"
									type="button"
									on:click={() => {
										showDeleteConfirmDialog = true;
									}}
								>
									{$i18n.t('Delete')}
								</button>
							{/if}
						</div>

						<button
							class="flex flex-row items-center space-x-1 rounded-full bg-black px-3.5 py-1.5 text-sm font-normal text-white transition hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100"
							type="submit"
						>
							{$i18n.t('Save')}
						</button>
					</div>
				</div>
			</form>
		</div>
	</div>
</Modal>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	message={$i18n.t(
		'Are you sure you want to delete this connection? This action cannot be undone.'
	)}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={() => {
		onDelete();
		show = false;
	}}
/>
