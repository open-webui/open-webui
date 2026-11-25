<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	const settingId = `image-connection-${uuidv4()}`;
	import { getContext } from 'svelte';
	const i18n = getContext<any>('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import ImageConnectionModal from './ImageConnectionModal.svelte';

	export let onDelete = () => {};
	export let onSubmit = (_connection: any) => {};

	export let connection: any = null;

	let showConfigModal = false;
</script>

<ImageConnectionModal
	edit
	bind:show={showConfigModal}
	{connection}
	onDelete={() => {
		onDelete();
		showConfigModal = false;
	}}
	onSubmit={(c: any) => {
		connection = c;
		onSubmit(c);
	}}
/>

<div
	class="group/setting-row flex w-full items-center gap-3 text-xs text-base-600 dark:text-base-400"
>
	<Tooltip className="w-full relative" content={connection?.url ?? ''} placement="top-start">
		<div class="flex w-full">
			<div
				class="flex-1 relative flex gap-1.5 items-center {!(connection?.config?.enable ?? true)
					? 'opacity-50'
					: ''}"
			>
				<Photo className="size-3.5" strokeWidth="1.5" />

				<button
					type="button"
					on:click={() => (showConfigModal = true)}
					class="w-full min-w-0 truncate text-left cursor-pointer bg-transparent outline-hidden text-base-600 dark:text-base-400 transition-colors duration-150 group-hover/setting-row:text-base-900 group-focus-within/setting-row:text-base-900 dark:group-hover/setting-row:text-white dark:group-focus-within/setting-row:text-white"
				>
					{connection?.name || connection?.url}
					<span class="text-base-500">{(connection?.config?.model_ids ?? []).join(', ')}</span>
				</button>
			</div>
		</div>
	</Tooltip>

	<div class="flex shrink-0 items-center gap-1">
		<Tooltip content={$i18n.t('Configure')} className="self-start">
			<button
				aria-label={$i18n.t('Configure')}
				class="flex size-6 items-center justify-center rounded-lg text-base-400 transition-colors hover:text-base-700 dark:text-base-600 dark:hover:text-base-300"
				on:click={() => {
					showConfigModal = true;
				}}
				type="button"
			>
				<Cog6 />
			</button>
		</Tooltip>

		<Tooltip
			content={(connection?.config?.enable ?? true) ? $i18n.t('Enabled') : $i18n.t('Disabled')}
		>
			<Switch
				id={`${settingId}-control`}
				state={connection?.config?.enable ?? true}
				ariaLabel={`${$i18n.t('Enabled')}: ${connection?.name || connection?.url}`}
				on:change={() => {
					connection = {
						...connection,
						config: { ...(connection?.config ?? {}), enable: !(connection?.config?.enable ?? true) }
					};
					onSubmit(connection);
				}}
			/>
		</Tooltip>
	</div>
</div>
