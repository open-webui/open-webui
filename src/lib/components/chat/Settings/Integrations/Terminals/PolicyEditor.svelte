<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import type { PolicyData } from '$lib/apis/terminal';
	import { createPolicy, updatePolicy } from '$lib/apis/terminal';

	export let show = false;
	export let edit = false;
	export let serverId = '';
	export let policy: { id: string; data: PolicyData } | null = null;
	export let onSave: () => void = () => {};

	let policyId = '';
	let image = '';
	let cpuLimit = '1';
	let memoryLimit = '1Gi';
	let storageType: 'ephemeral' | 'persistent' = 'ephemeral';
	let storageSize = '5Gi';
	let storageMode = 'per-user';
	let idleTimeoutMinutes = 30;
	let envPairs: { key: string; value: string }[] = [];

	let saving = false;

	const init = () => {
		if (policy) {
			policyId = policy.id;
			const d = policy.data ?? {};
			image = d.image ?? '';
			cpuLimit = d.cpu_limit ?? '1';
			memoryLimit = d.memory_limit ?? '1Gi';
			storageType = d.storage ? 'persistent' : 'ephemeral';
			storageSize = d.storage ?? '5Gi';
			storageMode = d.storage_mode ?? 'per-user';
			idleTimeoutMinutes = d.idle_timeout_minutes ?? 30;
			const env = d.env ?? {};
			envPairs = Object.entries(env).map(([k, v]) => ({ key: k, value: v }));
		} else {
			policyId = '';
			image = '';
			cpuLimit = '1';
			memoryLimit = '1Gi';
			storageType = 'ephemeral';
			storageSize = '5Gi';
			storageMode = 'per-user';
			idleTimeoutMinutes = 30;
			envPairs = [];
		}
	};

	$: if (show) {
		init();
	}

	const buildData = (): PolicyData => {
		const data: PolicyData = {};
		if (image) data.image = image;
		if (cpuLimit) data.cpu_limit = cpuLimit;
		if (memoryLimit) data.memory_limit = memoryLimit;
		if (storageType === 'persistent') {
			data.storage = storageSize;
			data.storage_mode = storageMode;
		}
		if (idleTimeoutMinutes > 0) data.idle_timeout_minutes = idleTimeoutMinutes;

		const env: Record<string, string> = {};
		for (const pair of envPairs) {
			if (pair.key.trim()) env[pair.key.trim()] = pair.value;
		}
		if (Object.keys(env).length > 0) data.env = env;
		return data;
	};

	const submitHandler = async () => {
		if (!policyId.trim()) {
			toast.error($i18n.t('Please enter a Policy ID'));
			return;
		}

		saving = true;
		try {
			const data = buildData();
			let result;
			if (edit) {
				result = await updatePolicy(localStorage.token, serverId, policyId, data);
			} else {
				result = await createPolicy(localStorage.token, serverId, policyId, data);
			}

			if (result) {
				toast.success($i18n.t('Policy saved'));
				onSave();
				show = false;
			} else {
				toast.error($i18n.t('Failed to save policy'));
			}
		} catch (err) {
			toast.error($i18n.t('Failed to save policy: {{error}}', { error: String(err) }));
		} finally {
			saving = false;
		}
	};

	const inputClass = (hc: boolean) =>
		`w-full flex-1 text-sm bg-transparent font-mono ${hc ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`;
	const labelClass = (hc: boolean) =>
		`text-xs ${hc ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`;

	$: hc = $settings?.highContrastMode ?? false;
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<h1 class="text-lg font-medium self-center font-primary">
				{#if edit}
					{$i18n.t('Edit Policy')}
				{:else}
					{$i18n.t('Create Policy')}
				{/if}
			</h1>
			<button class="self-center" aria-label={$i18n.t('Close')} on:click={() => (show = false)}>
				<XMark className="size-5" />
			</button>
		</div>

		<div class="flex flex-col w-full px-4 pb-4 dark:text-gray-200">
			<form class="flex flex-col w-full" on:submit|preventDefault={submitHandler}>
				<div class="px-1">
					<!-- Policy ID -->
					<div class="flex flex-col">
						<div class="flex justify-between mb-0.5">
							<label for="pe-policy-id" class={labelClass(hc)}>{$i18n.t('Policy ID')}</label>
						</div>
						<input
							id="pe-policy-id"
							class={inputClass(hc)}
							type="text"
							bind:value={policyId}
							placeholder="python-ds"
							autocomplete="off"
							disabled={edit}
						/>
					</div>

					<!-- Image -->
					<div class="flex flex-col mt-2">
						<div class="flex justify-between mb-0.5">
							<label for="pe-image" class={labelClass(hc)}>
								{$i18n.t('Image')}
								<span class="opacity-50">({$i18n.t('optional')})</span>
							</label>
						</div>
						<input
							id="pe-image"
							class={inputClass(hc)}
							type="text"
							bind:value={image}
							placeholder="ghcr.io/open-webui/open-terminal:latest"
							autocomplete="off"
						/>
					</div>

					<!-- CPU / Memory -->
					<div class="flex gap-2 mt-2">
						<div class="flex flex-col flex-1">
							<div class="flex justify-between mb-0.5">
								<label for="pe-cpu" class={labelClass(hc)}>{$i18n.t('CPU')}</label>
							</div>
							<input
								id="pe-cpu"
								class={inputClass(hc)}
								type="text"
								bind:value={cpuLimit}
								placeholder="1"
								autocomplete="off"
							/>
						</div>
						<div class="flex flex-col flex-1">
							<div class="flex justify-between mb-0.5">
								<label for="pe-memory" class={labelClass(hc)}>{$i18n.t('Memory')}</label>
							</div>
							<input
								id="pe-memory"
								class={inputClass(hc)}
								type="text"
								bind:value={memoryLimit}
								placeholder="1Gi"
								autocomplete="off"
							/>
						</div>
					</div>

					<!-- Storage -->
					<div class="flex gap-2 mt-2">
						<div class="flex flex-col flex-1">
							<div class="flex justify-between mb-0.5">
								<label class={labelClass(hc)}>{$i18n.t('Storage')}</label>
							</div>
							<div class="flex gap-2">
								<select
									class={`dark:bg-gray-900 w-auto text-sm bg-transparent pr-5 ${hc ? '' : 'outline-hidden'}`}
									bind:value={storageType}
								>
									<option value="ephemeral">{$i18n.t('Ephemeral')}</option>
									<option value="persistent">{$i18n.t('Persistent')}</option>
								</select>
								{#if storageType === 'persistent'}
									<input
										class={inputClass(hc)}
										type="text"
										bind:value={storageSize}
										placeholder="5Gi"
										autocomplete="off"
									/>
								{/if}
							</div>
						</div>

						{#if storageType === 'persistent'}
							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class={labelClass(hc)}>{$i18n.t('Storage Mode')}</label>
								</div>
								<select
									class={`dark:bg-gray-900 w-full text-sm bg-transparent pr-5 ${hc ? '' : 'outline-hidden'}`}
									bind:value={storageMode}
								>
									<option value="per-user">{$i18n.t('Per User')}</option>
									<option value="shared">{$i18n.t('Shared (RWX)')}</option>
									<option value="shared-rwo">{$i18n.t('Shared (RWO)')}</option>
								</select>
							</div>
						{/if}
					</div>

					<!-- Idle Timeout -->
					<div class="flex flex-col mt-2">
						<div class="flex justify-between mb-0.5">
							<label for="pe-idle" class={labelClass(hc)}>
								{$i18n.t('Idle Timeout')}
								<span class="opacity-50">({$i18n.t('min')})</span>
							</label>
						</div>
						<input
							id="pe-idle"
							class={inputClass(hc)}
							type="number"
							min="0"
							bind:value={idleTimeoutMinutes}
							placeholder="30"
							autocomplete="off"
						/>
					</div>

					<!-- Env Vars -->
					<div class="flex flex-col mt-2">
						<div class="flex justify-between items-center mb-0.5">
							<span class={labelClass(hc)}>{$i18n.t('Environment Variables')}</span>
							<button
								type="button"
								class="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
								on:click={() => (envPairs = [...envPairs, { key: '', value: '' }])}
							>
								+ {$i18n.t('Add')}
							</button>
						</div>
						{#each envPairs as pair, idx}
							<div class="flex gap-1.5 mb-1">
								<input
									class={`flex-1 text-sm bg-transparent font-mono ${hc ? '' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
									type="text"
									bind:value={pair.key}
									placeholder="KEY"
								/>
								<input
									class={`flex-[2] text-sm bg-transparent font-mono ${hc ? '' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
									type="text"
									bind:value={pair.value}
									placeholder="value"
								/>
								<button
									type="button"
									class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition px-1"
									on:click={() => (envPairs = envPairs.filter((_, i) => i !== idx))}
								>
									<XMark className="size-3" />
								</button>
							</div>
						{/each}
					</div>

					<!-- Submit -->
					<div class="flex justify-end pt-3">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
							type="submit"
							disabled={saving}
						>
							{saving ? $i18n.t('Saving...') : $i18n.t('Save')}
						</button>
					</div>
				</div>
			</form>
		</div>
	</div>
</Modal>
