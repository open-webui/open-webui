<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { updateUserSettings } from '$lib/apis/users';
	import { settings } from '$lib/stores';

	const i18n = getContext('i18n');

	export let show = false;
	export let serverName: string = '';
	export let serverId: string = '';
	export let placeholders: string[] = [];

	let placeholderValues: { [key: string]: string } = {};

	$: if (show && placeholders) {
		// Initialize values from settings
		const savedValues = $settings?.tool_server_placeholders?.[serverId] || {};
		placeholderValues = placeholders.reduce((acc, placeholder) => {
			acc[placeholder] = savedValues[placeholder] || '';
			return acc;
		}, {} as { [key: string]: string });
	}

	const saveHandler = async () => {
		try {
			const currentPlaceholders = $settings?.tool_server_placeholders || {};
			const updatedPlaceholders = {
				...currentPlaceholders,
				[serverId]: placeholderValues
			};

			await updateUserSettings(localStorage.token, {
				tool_server_placeholders: updatedPlaceholders
			});

			// Update local settings
			settings.set({
				...$settings,
				tool_server_placeholders: updatedPlaceholders
			});

			toast.success($i18n.t('Placeholder values saved'));
			show = false;
		} catch (error) {
			toast.error($i18n.t('Failed to save placeholder values'));
			console.error('Error saving placeholder values:', error);
		}
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-2">
			<h1 class="text-lg font-medium self-center font-primary">
				{$i18n.t('Configure Placeholders')}
			</h1>
		</div>

		<div class="flex flex-col px-5 pb-4">
			<div class="mb-3">
				<div class="text-sm font-medium mb-1">{serverName}</div>
				<div class="text-xs text-gray-500">
					{$i18n.t(
						'These values will be used to replace placeholders in the server headers. Your values are private and only visible to you.'
					)}
				</div>
			</div>

			<form
				on:submit|preventDefault={saveHandler}
				class="flex flex-col gap-3"
			>
				{#each placeholders as placeholder}
					<div class="flex flex-col gap-1">
						<label
							for={`placeholder-${placeholder}`}
							class="text-xs font-medium text-gray-600 dark:text-gray-400"
						>
							{placeholder}
						</label>
						<SensitiveInput
							id={`placeholder-${placeholder}`}
							bind:value={placeholderValues[placeholder]}
							placeholder={$i18n.t(`Enter value for {{placeholder}}`, { placeholder })}
							required={false}
						/>
						<div class="text-xs text-gray-500">
							{$i18n.t('Used in headers as')} <code class="text-xs">{'{{' + placeholder + '}}'}</code>
						</div>
					</div>
				{/each}

				<div class="flex justify-end pt-3 gap-2">
					<button
						class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-gray-900 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full"
						type="button"
						on:click={() => {
							show = false;
						}}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						type="submit"
					>
						{$i18n.t('Save')}
					</button>
				</div>
			</form>
		</div>
	</div>
</Modal>
