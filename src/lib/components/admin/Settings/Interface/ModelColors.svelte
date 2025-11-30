<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Sortable from 'sortablejs';
	import { getContext } from 'svelte';
	import type { ModelColorsConfig, ModelColorMapping } from '$lib/types';

	const i18n = getContext('i18n');

	export let config: ModelColorsConfig;
	export let models: { id: string; name: string }[] = [];

	let sortable: Sortable | null = null;
	let mappingListElement: HTMLElement | null = null;

	const positionChangeHandler = () => {
		if (!mappingListElement) return;
		const mappingIdOrder = Array.from(mappingListElement.children).map((child) =>
			child.id.replace('mapping-item-', '')
		);

		config.mappings = mappingIdOrder.map((pattern) => {
			const index = config.mappings.findIndex((m) => m.pattern === pattern);
			return config.mappings[index];
		});
	};

	$: if (config.mappings) {
		initSortable();
	}

	const initSortable = () => {
		if (sortable) {
			sortable.destroy();
		}

		if (mappingListElement) {
			sortable = new Sortable(mappingListElement, {
				animation: 150,
				handle: '.item-handle',
				onUpdate: async () => {
					positionChangeHandler();
				}
			});
		}
	};

	const addMapping = () => {
		const lastMapping = config.mappings.at(-1);
		if (config.mappings.length === 0 || (lastMapping && lastMapping.pattern !== '')) {
			config.mappings = [
				...config.mappings,
				{
					pattern: '',
					color: '#3b82f6',
					priority: 0
				}
			];
		}
	};

	const removeMapping = (index: number) => {
		config.mappings.splice(index, 1);
		config.mappings = config.mappings;
	};
</script>

<div class="space-y-3">
	<div class="flex w-full items-center justify-between">
		<div class="self-center text-xs font-medium">
			{$i18n.t('Enable Model Accent Colors')}
		</div>
		<Switch bind:state={config.enabled} />
	</div>

	{#if config.enabled}
		<div class="space-y-3">
			<div class="flex items-center gap-3">
				<div class="text-xs">{$i18n.t('Default Color')}</div>
				<input
					type="color"
					class="w-8 h-8 rounded cursor-pointer border border-gray-200 dark:border-gray-700"
					bind:value={config.defaultColor}
				/>
				<input
					type="text"
					class="w-24 text-xs bg-transparent outline-none border-b border-gray-300 dark:border-gray-600"
					bind:value={config.defaultColor}
					placeholder="#3b82f6"
				/>
			</div>

			<div class="flex w-full justify-between items-center">
				<div class="self-center text-xs">
					{$i18n.t('Model Color Mappings')}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded-sm transition"
					type="button"
					on:click={addMapping}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
						/>
					</svg>
				</button>
			</div>

			<div
				class="flex flex-col gap-3 {config.mappings?.length > 0 ? 'mt-2' : ''}"
				bind:this={mappingListElement}
			>
				{#each config.mappings as mapping, idx (mapping.pattern || idx)}
					<div
						class="flex justify-between items-center -ml-1"
						id="mapping-item-{mapping.pattern || idx}"
					>
						<EllipsisVertical className="size-4 cursor-move item-handle" />

						<div class="flex flex-row flex-1 gap-2 items-center">
							<input
								type="text"
								list="model-suggestions"
								class="flex-1 text-xs bg-transparent outline-none border-b border-gray-300 dark:border-gray-600 px-1 py-1"
								placeholder={$i18n.t('Model ID or pattern (e.g., gpt-*, claude-*)')}
								bind:value={mapping.pattern}
							/>

							<input
								type="color"
								class="w-7 h-7 rounded cursor-pointer border border-gray-200 dark:border-gray-700"
								bind:value={mapping.color}
							/>

							<input
								type="text"
								class="w-20 text-xs bg-transparent outline-none border-b border-gray-300 dark:border-gray-600"
								bind:value={mapping.color}
								placeholder="#hex"
							/>

							<Tooltip content={$i18n.t('Priority (higher = checked first)')}>
								<input
									type="number"
									class="w-12 text-xs bg-transparent outline-none border-b border-gray-300 dark:border-gray-600 text-center"
									bind:value={mapping.priority}
									min="0"
									placeholder="0"
								/>
							</Tooltip>
						</div>

						<button class="pr-3 pl-2" type="button" on:click={() => removeMapping(idx)}>
							<XMark className={'size-4'} />
						</button>
					</div>
				{/each}
			</div>

			{#if models.length > 0}
				<datalist id="model-suggestions">
					{#each models as model}
						<option value={model.id}>{model.name}</option>
					{/each}
				</datalist>
			{/if}

			<div class="text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Use * as wildcard (e.g., gpt-* matches all GPT models). Higher priority mappings are checked first.')}
			</div>
		</div>
	{/if}
</div>
