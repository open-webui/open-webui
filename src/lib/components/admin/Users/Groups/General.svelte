<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getModelsConfig } from '$lib/apis/configs';
	import { models } from '$lib/stores';
	import ModelSelector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext<import('svelte/store').Writable<import('i18next').i18n>>('i18n');

	export let name = '';
	export let color = '';
	export let description = '';
	export let data: Record<string, any> = {};

	export let edit = false;
	export let groupId: string | undefined = undefined;
	export let groups: import('../Groups.svelte').GroupListItem[] = [];
	export let parent_group_id: string | null = null;
	let parentSearch = '';
	let showParents = false;
	$: selectedParent = groups.find((group) => group.id === parent_group_id);
	$: candidates = groups
		.filter(
			(group) =>
				group.id !== groupId &&
				(!groupId || !group.ancestor_ids.includes(groupId)) &&
				(group.id === parent_group_id ||
					group.path.toLowerCase().includes(parentSearch.toLowerCase()))
		)
		.sort((a, b) => a.path.localeCompare(b.path));
	$: if (!Array.isArray(data?.config?.default_models)) {
		data = { ...data, config: { ...data?.config, default_models: [] } };
	}
	$: modelItems = [
		...$models.map((model) => ({ value: model.id, label: model.name || model.id, model })),
		...(data?.config?.default_models ?? [])
			.filter((id: string) => !$models.some((model) => model.id === id))
			.map((id: string) => ({
				value: id,
				label: id,
				model: { id, name: id, owned_by: 'openai' as const, external: false }
			}))
	];
	let globalDefaultModels: string[] = [];
	onMount(async () => {
		try {
			const modelConfig = await getModelsConfig(localStorage.token);
			globalDefaultModels = modelConfig.DEFAULT_MODELS?.split(',').filter(Boolean) ?? [];
		} catch (error) {
			toast.error(String(error));
		}
	});
	$: {
		inheritedModelIds = globalDefaultModels;
		inheritedModelSource = $i18n.t('Global defaults');
		const seen = new Set<string>();
		let parent = groups.find((group) => group.id === parent_group_id);
		while (parent && !seen.has(parent.id)) {
			seen.add(parent.id);
			if (parent.data?.config?.default_models?.length) {
				inheritedModelIds = parent.data.config.default_models;
				inheritedModelSource = parent.path;
				break;
			}
			parent = groups.find((group) => group.id === parent?.parent_group_id);
		}
	}
	let inheritedModelIds: string[] = [];
	let inheritedModelSource = '';
	export let onDelete: Function = () => {};
</script>

<div class="flex gap-2">
	<div class="flex flex-col w-full">
		<div class=" mb-0.5 text-xs text-gray-500">{$i18n.t('Name')}</div>

		<div class="flex-1">
			<input
				class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
				type="text"
				bind:value={name}
				placeholder={$i18n.t('Group Name')}
				autocomplete="off"
				required
			/>
		</div>
	</div>
</div>

<div class="my-3 space-y-1">
	<div class="flex items-center justify-between gap-3">
		<Tooltip content={$i18n.t('Members of this group inherit access from its parent groups.')}>
			<label for="group-parent" class="text-xs shrink-0 text-gray-500"
				>{$i18n.t('Parent group')}</label
			>
		</Tooltip>
		<Dropdown
			align="end"
			bind:show={showParents}
			contentClass="w-80 max-w-[calc(100vw-2rem)]"
			maxHeight="20rem"
			onOpenChange={(open) => {
				if (!open) parentSearch = '';
			}}
		>
			<button
				id="group-parent"
				type="button"
				aria-haspopup="menu"
				aria-expanded={showParents}
				class="flex max-w-64 items-center gap-1.5 rounded-lg px-1.5 py-1 text-sm text-gray-700 transition hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-900"
			>
				<span class="min-w-0 flex-1 truncate">{selectedParent?.name ?? $i18n.t('No parent')}</span>
				<ChevronDown className="size-3.5 shrink-0 text-gray-400" />
			</button>
			<div slot="content">
				<DropdownMenu className="w-full">
					<div class="flex items-center gap-2 px-2 py-2">
						<Search className="size-3.5 shrink-0 text-gray-400" />
						<input
							aria-label={$i18n.t('Search parent groups')}
							placeholder={$i18n.t('Search parent groups')}
							class="min-w-0 w-full bg-transparent text-sm outline-hidden"
							bind:value={parentSearch}
						/>
					</div>
					<button
						type="button"
						role="menuitemradio"
						aria-checked={!parent_group_id}
						class="my-1 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={() => {
							parent_group_id = null;
							showParents = false;
						}}
					>
						<span class="flex-1">{$i18n.t('No parent')}</span>
						{#if !parent_group_id}<Check className="size-4" />{/if}
					</button>
					{#each candidates as candidate (candidate.id)}
						<button
							type="button"
							role="menuitemradio"
							aria-checked={candidate.id === parent_group_id}
							class="relative flex w-full items-center gap-2 rounded-lg py-2 pr-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-800"
							title={candidate.path}
							on:click={() => {
								parent_group_id = candidate.id;
								showParents = false;
							}}
						>
							{#if candidate.ancestor_ids.length}<span
									aria-hidden="true"
									class="absolute top-0 h-1/2 w-2 border-b border-l border-gray-200 dark:border-gray-700"
									style:left={`${Math.min(candidate.ancestor_ids.length, 6) * 16 - 4}px`}
								></span>{/if}
							<span
								class="flex-1 truncate"
								style:margin-left={`${Math.min(candidate.ancestor_ids.length, 6) * 16}px`}
								>{candidate.name}</span
							>
							{#if candidate.id === parent_group_id}<Check className="size-4 shrink-0" />{/if}
						</button>
					{:else}<p class="px-2 py-3 text-xs text-gray-500">{$i18n.t('No groups found')}</p>{/each}
				</DropdownMenu>
			</div>
		</Dropdown>
	</div>
</div>

<div class="mb-3 space-y-1">
	<div class="flex items-center justify-between gap-3">
		<Tooltip
			content={$i18n.t(
				'Leave unset to inherit default models. Personal model selections take precedence.'
			)}
		>
			<label for="model-selector-group-defaults-button" class="shrink-0 text-xs text-gray-500"
				>{$i18n.t('Default models')}</label
			>
		</Tooltip>
		<div class="flex min-w-0 max-w-[65%] items-center gap-2">
			{#if data?.config?.default_models?.length}
				<button
					type="button"
					class="shrink-0 whitespace-nowrap text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
					on:click={() => {
						data = { ...data, config: { ...data.config, default_models: [] } };
					}}
				>
					{$i18n.t('Inherit')}
				</button>
			{/if}
			<div class="min-w-0 flex-1">
				<ModelSelector
					id="group-defaults"
					items={modelItems}
					bind:values={data.config.default_models}
					compareEnabled={true}
					selectionOnly={true}
					includeHidden={true}
					placeholder={$i18n.t('Inherit')}
					triggerClassName="text-sm"
					align="end"
				/>
			</div>
		</div>
	</div>
	{#if !data?.config?.default_models?.length}
		<p class="text-xs text-gray-500">
			{inheritedModelSource}{inheritedModelIds.length ? ': ' : ''}{inheritedModelIds
				.map((id) => $models.find((model) => model.id === id)?.name || id)
				.join(', ')}
		</p>
	{/if}
</div>

<!-- <div class="flex flex-col w-full mt-2">
	<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Color')}</div>

	<div class="flex-1">
		<Tooltip content={$i18n.t('Hex Color - Leave empty for default color')} placement="top-start">
			<div class="flex gap-0.5">
				<div class="text-gray-500">#</div>

				<input
					class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
					type="text"
					bind:value={color}
					placeholder={$i18n.t('Hex Color')}
					autocomplete="off"
				/>
			</div>
		</Tooltip>
	</div>
</div> -->

<div class="flex flex-col w-full mt-2">
	<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Description')}</div>

	<div class="flex-1">
		<Textarea
			className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden resize-none"
			rows={4}
			bind:value={description}
			placeholder={$i18n.t('Group Description')}
		/>
	</div>
</div>

<hr class="border-gray-50 dark:border-gray-850/30 my-1" />

<div class="flex flex-col w-full mt-2">
	<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Setting')}</div>

	<div>
		<div class=" flex w-full justify-between">
			<div class=" self-center text-xs">
				{$i18n.t('Who can share to this group')}
			</div>

			<div class="flex items-center gap-2 p-1">
				<select
					class="text-sm bg-transparent outline-hidden rounded-lg pl-2 pr-5"
					value={data?.config?.share ?? 'members'}
					on:change={(e) => {
						const value = e.currentTarget.value;
						let shareValue;
						if (value === 'false') {
							shareValue = false;
						} else if (value === 'true') {
							shareValue = true;
						} else {
							shareValue = value;
						}
						data.config = { ...(data?.config ?? {}), share: shareValue };
					}}
				>
					<option value={false}>{$i18n.t('No one')}</option>
					<option value="members">{$i18n.t('Members')}</option>
					<option value={true}>{$i18n.t('Anyone')}</option>
				</select>
			</div>
		</div>
	</div>
</div>

{#if edit}
	<div class="flex flex-col w-full mt-2">
		<div class=" mb-0.5 text-xs text-gray-500">{$i18n.t('Actions')}</div>

		<div class="flex-1">
			<button
				class="text-xs bg-transparent hover:underline cursor-pointer"
				type="button"
				on:click={() => onDelete()}
			>
				{$i18n.t('Delete')}
			</button>
		</div>
	</div>
{/if}
