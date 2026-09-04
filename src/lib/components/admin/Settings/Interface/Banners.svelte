<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import LocalizedField from '$lib/components/common/LocalizedField.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Sortable from 'sortablejs';
	import { getContext } from 'svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	const i18n = getContext('i18n');

	export let banners = [];
	export let locale = '';

	const positionChangeHandler = (bannerListElement: HTMLElement) => {
		const bannerIdOrder = Array.from(bannerListElement.children).map((child) =>
			child.id.replace('banner-item-', '')
		);

		// Sort the banners array based on the new order
		banners = bannerIdOrder.map((id) => {
			const index = banners.findIndex((banner) => banner.id === id);
			return banners[index];
		});
	};

	const init = (node: HTMLElement) => {
		const sortable = new Sortable(node, {
			animation: 150,
			handle: '.item-handle',
			onUpdate: () => positionChangeHandler(node)
		});
		return { destroy: () => sortable.destroy() };
	};
</script>

<div class="flex flex-col gap-1.5" use:init>
	{#each banners as banner, bannerIdx (banner.id)}
		<div
			class="flex items-start gap-1 rounded-lg border border-gray-100/40 bg-transparent px-2 py-1 transition focus-within:border-gray-300 dark:border-gray-850/50 dark:focus-within:border-gray-600"
			id="banner-item-{banner.id}"
		>
			<Tooltip content={$i18n.t('Reorder')}>
				<div
					class="item-handle flex h-6 w-3 shrink-0 cursor-move items-center justify-center text-gray-400 dark:text-gray-600"
				>
					<EllipsisVertical className="size-3.5" />
				</div>
			</Tooltip>
			<div class="flex min-w-0 flex-1 flex-col gap-0.5 sm:flex-row sm:items-start sm:gap-2">
				<SettingsSelect
					bind:value={banner.type}
					required
					ariaLabel={$i18n.t('Type')}
					className="w-24 max-w-full shrink-0"
					selectClassName="!h-6 !border-transparent !bg-transparent !ps-1 capitalize dark:!bg-transparent"
				>
					<option value="" disabled hidden class="text-gray-900">{$i18n.t('Type')}</option>
					<option value="info" class="text-gray-900">{$i18n.t('Info')}</option>
					<option value="warning" class="text-gray-900">{$i18n.t('Warning')}</option>
					<option value="error" class="text-gray-900">{$i18n.t('Error')}</option>
					<option value="success" class="text-gray-900">{$i18n.t('Success')}</option>
				</SettingsSelect>
				<div class="w-full min-w-0 flex-1 sm:pt-0.5">
					<LocalizedField
						className="block min-h-5 max-h-40 w-full resize-none bg-transparent text-[0.8125rem] leading-5 text-gray-700 outline-hidden placeholder:text-gray-300 dark:text-gray-200 dark:placeholder:text-gray-700 [field-sizing:content]"
						placeholder={$i18n.t('Content')}
						bind:value={banner.content}
						bind:translations={banner.i18n}
						{locale}
						field="content"
						multiline
						rows={1}
					/>
				</div>
			</div>
			<div class="flex h-6 shrink-0 items-center px-1">
				<Switch
					bind:state={banner.dismissible}
					ariaLabel={$i18n.t('Remember Dismissal')}
					tooltip={$i18n.t('Remember Dismissal')}
				/>
			</div>
			<Tooltip content={$i18n.t('Delete')}>
				<button
					class="flex size-6 shrink-0 items-center justify-center text-gray-400 opacity-70 transition hover:text-gray-700 hover:opacity-100 dark:text-gray-600 dark:hover:text-gray-300"
					type="button"
					aria-label={$i18n.t('Delete')}
					on:click={() => {
						banners.splice(bannerIdx, 1);
						banners = banners;
					}}
				>
					<XMark className="size-3.5" />
				</button>
			</Tooltip>
		</div>
	{/each}
</div>
