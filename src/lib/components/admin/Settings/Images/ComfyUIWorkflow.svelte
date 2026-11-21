<script lang="ts">
	import { getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import CodeEditorModal from '$lib/components/common/CodeEditorModal.svelte';

	const i18n: any = getContext('i18n');

	type WorkflowNode = { type: string; key: string; node_ids: string };

	export let id: string;
	export let label: string;
	export let description = '';
	export let workflow = '';
	export let nodes: WorkflowNode[] = [];
	export let requiredTypes: string[] = ['prompt'];
	export let requiredNote = '';

	const inputClass =
		'w-full bg-transparent text-sm outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700';

	let showEditor = false;
	let fileInputElement: HTMLInputElement;
</script>

<div class="flex flex-col w-full mt-2">
	<input
		bind:this={fileInputElement}
		hidden
		type="file"
		accept=".json"
		on:change={(e) => {
			const target = e.currentTarget;
			const file = target.files?.[0];
			if (!file) return;

			const reader = new FileReader();
			reader.onload = (event) => {
				workflow = `${event.target?.result ?? ''}`;
				target.value = '';
			};
			reader.readAsText(file);
		}}
	/>

	<div class="flex justify-between items-center">
		<div>
			<div class="text-xs text-base-500">{label}</div>
			{#if description}
				<div class="text-xs text-base-400 dark:text-base-600">{description}</div>
			{/if}
		</div>

		<div class="flex items-center gap-2 shrink-0">
			<!-- Always available, so a workflow can be pasted in as well as uploaded. -->
			<button
				class="text-xs text-base-500 transition-colors hover:text-base-900 hover:underline dark:hover:text-base-0"
				type="button"
				aria-label={$i18n.t('settings.admin.images.editWorkflowJsonContent.label')}
				on:click={() => {
					showEditor = true;
				}}
			>
				{$i18n.t('Edit')}
			</button>

			<Tooltip content={$i18n.t('settings.admin.images.clickHereToUploadAWorkflowJsonFile.label')}>
				<button
					class="text-xs text-base-500 transition-colors hover:text-base-900 hover:underline dark:hover:text-base-0"
					type="button"
					aria-label={$i18n.t('settings.admin.images.clickHereToUploadAWorkflowJsonFile.label')}
					on:click={() => {
						fileInputElement?.click();
					}}
				>
					{$i18n.t('Upload')}
				</button>
			</Tooltip>
		</div>
	</div>

	<CodeEditorModal
		bind:show={showEditor}
		value={workflow}
		lang="json"
		title={label}
		description={$i18n.t('Paste or edit a workflow exported as API format from ComfyUI.')}
		onChange={(value: string) => {
			workflow = value;
		}}
	/>

	{#if workflow}
		<div class="flex flex-col gap-1.5 mt-1.5 text-xs">
			{#each nodes as node}
				<div class="flex w-full items-center">
					<label
						for={`${id}-node-${node.type}-key`}
						class="capitalize line-clamp-1 w-20 shrink-0 text-base-400 dark:text-base-500"
					>
						{node.type}{requiredTypes.includes(node.type) ? '*' : ''}
					</label>

					<Tooltip content={$i18n.t('Input Key (e.g. text, unet_name, steps)')}>
						<input
							id={`${id}-node-${node.type}-key`}
							class="{inputClass} w-24"
							placeholder={$i18n.t('Key')}
							bind:value={node.key}
							required
						/>
					</Tooltip>

					<div class="px-2 text-base-400 dark:text-base-500">:</div>

					<Tooltip
						className="w-full"
						content={$i18n.t('Comma separated Node Ids (e.g. 1 or 1,2)')}
						placement="top-start"
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('Node Ids')}
							aria-label={$i18n.t('Node Ids')}
							bind:value={node.node_ids}
						/>
					</Tooltip>
				</div>
			{/each}
		</div>

		<div class="mt-1 text-xs text-base-400 dark:text-base-500">
			{requiredNote || $i18n.t('*Prompt node ID(s) are required for image generation')}
		</div>
	{/if}
</div>
