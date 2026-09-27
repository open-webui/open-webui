<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { settings } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';

	const i18n = getContext<any>('i18n');

	export let show = false;
	export let tool: any = null;
	export let onSave: Function = () => {};

	let token = '';

	$: if (show && tool) {
		const keys = $settings?.tool_server_keys ?? {};
		token = keys[tool.id] ?? keys[tool.url] ?? '';
	}

	const saveHandler = async () => {
		if (!tool) return;
		const toolServerKeys = {
			...($settings?.tool_server_keys ?? {}),
			[tool.id]: token
		};
		if (tool.url) {
			toolServerKeys[tool.url] = token;
		}

		settings.update((s) => ({
			...s,
			tool_server_keys: toolServerKeys
		}));

		await updateUserSettings(localStorage.token, {
			ui: {
				tool_server_keys: toolServerKeys
			}
		}).catch((err) => {
			console.error(err);
			toast.error($i18n.t('Failed to save key'));
		});

		toast.success($i18n.t('API key saved'));
		show = false;
		onSave(token);
	};
</script>

<Modal bind:show size="sm">
	<div class="p-5 text-gray-800 dark:text-gray-100 flex flex-col gap-4">
		<div class="flex items-center justify-between border-b pb-3 dark:border-gray-800">
			<h3 class="text-base font-medium">
				{tool?.name ?? $i18n.t('Tool Authentication')}
			</h3>
		</div>

		{#if tool?.meta?.auth_instruction || tool?.auth_instruction}
			<div class="text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/60 p-3 rounded-lg border border-gray-100 dark:border-gray-800">
				{tool?.meta?.auth_instruction || tool?.auth_instruction}
			</div>
		{:else}
			<div class="text-sm text-gray-500">
				{$i18n.t('Please enter your personal API key or token to use this tool.')}
			</div>
		{/if}

		<div class="flex flex-col gap-1.5">
			<label for="user-tool-token" class="text-xs font-medium text-gray-500">
				{$i18n.t('API Key / Token')}
			</label>
			<SensitiveInput
				bind:value={token}
				placeholder={$i18n.t('Enter your token here')}
				required={false}
			/>
		</div>

		<div class="flex justify-end gap-2 pt-2">
			<button
				type="button"
				class="px-3.5 py-1.5 text-sm font-medium rounded-lg text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 transition"
				on:click={() => (show = false)}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				type="button"
				class="px-3.5 py-1.5 text-sm font-medium rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition disabled:opacity-50"
				on:click={saveHandler}
			>
				{$i18n.t('Save')}
			</button>
		</div>
	</div>
</Modal>
