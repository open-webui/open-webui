<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { getToolServerUserSecretsSpec, updateToolServerUserSecrets } from '$lib/apis/tools';

	const i18n = getContext<any>('i18n');

	export let show = false;
	export let id = '';
	export let name = '';

	let loading = false;
	let saving = false;
	let spec: any = null;
	let values: Record<string, string> = {};
	$: userSecretProperties = Object.entries((spec?.properties ?? {}) as Record<string, any>) as [
		string,
		any
	][];

	const load = async () => {
		if (!id) return;
		loading = true;
		try {
			spec = await getToolServerUserSecretsSpec(localStorage.token, id);
			values = {};
		} catch (error) {
			toast.error(`${error}`);
			show = false;
		} finally {
			loading = false;
		}
	};

	const save = async () => {
		saving = true;
		try {
			const payload = Object.fromEntries(
				Object.entries(values).filter(([, value]) => value !== undefined && value !== '')
			);
			await updateToolServerUserSecrets(localStorage.token, id, payload);
			toast.success($i18n.t('Credentials saved'));
			show = false;
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};

	$: if (show && id) {
		load();
	}
</script>

<Modal bind:show size="sm">
	<div>
		<div class="flex justify-between dark:text-gray-100 px-4 pt-3 pb-1">
			<div class="self-center text-sm font-medium">
				{$i18n.t('Configure credentials')}{name ? ` · ${name}` : ''}
			</div>
			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close')}
				on:click={() => (show = false)}
			>
				<XMark className="size-4" />
			</button>
		</div>

		{#if loading}
			<div class="flex justify-center px-4 py-6"><Spinner className="size-5" /></div>
		{:else if spec}
			<form class="px-4 pb-4" on:submit|preventDefault={save}>
				<p class="mb-3 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('These values are stored per user and are never shown back in the interface.')}
				</p>

				{#each userSecretProperties as [field, fieldSpec]}
					{@const configured = (spec.configured ?? []).includes(field)}
					{@const required = (spec.required ?? []).includes(field)}
					<div class="mb-3">
						<label class="mb-1 block text-xs text-gray-500" for="user-secret-{field}">
							{fieldSpec.title ?? field}
							{#if required}<span class="text-gray-400"> ({$i18n.t('required')})</span>{/if}
						</label>
						{#if fieldSpec.description}
							<div class="mb-1 text-xs text-gray-500">{fieldSpec.description}</div>
						{/if}
						<SensitiveInput
							id="user-secret-{field}"
							bind:value={values[field]}
							placeholder={configured
								? $i18n.t('Configured — enter a new value to replace it')
								: field}
							type={fieldSpec.format === 'password' ? 'password' : 'text'}
							required={required && !configured}
						/>
					</div>
				{/each}

				<div class="flex justify-end pt-1">
					<button
						class="px-3 py-1.5 text-sm bg-black text-white dark:bg-white dark:text-black rounded-full flex items-center gap-2 disabled:opacity-50"
						type="submit"
						disabled={saving}
					>
						{$i18n.t('Save')}
						{#if saving}<Spinner className="size-4" />{/if}
					</button>
				</div>
			</form>
		{/if}
	</div>
</Modal>
