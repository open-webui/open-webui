<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';
	import Sortable from 'sortablejs';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	export let banners = [];

	let sortable = null;
	let bannerListElement = null;

	const positionChangeHandler = () => {
		const bannerIdOrder = Array.from(bannerListElement.children).map((child) =>
			child.id.replace('banner-item-', '')
		);

		// Sort the banners array based on the new order
		banners = bannerIdOrder.map((id) => {
			const index = banners.findIndex((banner) => banner.id === id);
			return banners[index];
		});
	};

	$: if (banners) {
		init();
	}

	const init = () => {
		if (sortable) {
			sortable.destroy();
		}

		if (bannerListElement) {
			sortable = Sortable.create(bannerListElement, {
				animation: 150,
				handle: '.item-handle',
				onUpdate: async (event) => {
					positionChangeHandler();
				}
			});
		}
	};
</script>

<div class=" flex flex-col space-y-0.5" bind:this={bannerListElement}>
	{#each banners as banner, bannerIdx (banner.id)}
		<div class=" flex justify-between items-center -ml-1" id="banner-item-{banner.id}">
			<EllipsisVertical className="size-4 cursor-move item-handle" />

			<div class="flex flex-row flex-1 gap-2 items-center">
				<select
					class="w-fit capitalize rounded-xl text-xs bg-transparent outline-hidden text-left pl-1 pr-2"
					bind:value={banner.type}
					required
				>
					{#if banner.type == ''}
						<option value="" selected disabled class="text-gray-900">{$i18n.t('Type')}</option>
					{/if}
					<option value="info" class="text-gray-900">{$i18n.t('Info')}</option>
					<option value="warning" class="text-gray-900">{$i18n.t('Warning')}</option>
					<option value="error" class="text-gray-900">{$i18n.t('Error')}</option>
					<option value="success" class="text-gray-900">{$i18n.t('Success')}</option>
				</select>

				<input
					class="pr-5 py-1.5 text-xs w-full bg-transparent outline-hidden"
					placeholder={$i18n.t('Content')}
					bind:value={banner.content}
				/>

				<div class="relative -left-2">
					<Tooltip content={$i18n.t('Dismissible')} className="flex h-fit items-center">
						<Switch bind:state={banner.dismissible} />
					</Tooltip>
				</div>
			</div>

			<button
				class="pr-3"
				type="button"
				on:click={() => {
					banners.splice(bannerIdx, 1);
					banners = banners;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-4 h-4"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
	{/each}
</div>
