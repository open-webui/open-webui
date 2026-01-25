<script lang="ts">
	import { getContext } from 'svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let name = '';
	export let color = '';
	export let description = '';
	export let data = {};

	export let edit = false;
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
					class="text-sm bg-transparent dark:bg-gray-900 outline-hidden rounded-lg px-2"
					value={data?.config?.share ?? true}
					on:change={(e) => {
						const value = e.target.value;
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
