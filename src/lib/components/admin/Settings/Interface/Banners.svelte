<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
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

	const classNames: Record<string, string> = {
		info: 'bg-blue-500/20 text-blue-700 dark:text-blue-200 ',
		success: 'bg-green-500/20 text-green-700 dark:text-green-200',
		warning: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200',
		error: 'bg-red-500/20 text-red-700 dark:text-red-200'
	};

	$: if (banners) {
		init();
	}

	const init = () => {
		if (sortable) {
			sortable.destroy();
		}

		if (bannerListElement) {
			sortable = new Sortable(bannerListElement, {
				animation: 150,
				handle: '.item-handle',
				onUpdate: async (event) => {
					positionChangeHandler();
				}
			});
		}
	};
</script>

<div class=" flex flex-col gap-3 {banners?.length > 0 ? 'mt-2' : ''}" bind:this={bannerListElement}>
	{#each banners as banner, bannerIdx (banner.id)}
		<div class=" flex justify-between items-start -ml-1" id="banner-item-{banner.id}">
			<EllipsisVertical className="size-4 cursor-move item-handle" />

			<div class="flex flex-row flex-1 gap-2 items-start">
				<select
					class="w-fit capitalize rounded-xl text-xs bg-transparent outline-hidden pl-1 pr-5"
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

				<Textarea
					className="mr-2 text-xs w-full bg-transparent outline-hidden resize-none"
					placeholder={$i18n.t('Content')}
					bind:value={banner.content}
					maxSize={100}
				/>

				<div class="relative -left-2 flex items-center gap-1">
					<Switch bind:state={banner.dismissible} tooltip={true} />
					<Tooltip content={$i18n.t('Remember Dismissal')}>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="size-3.5 text-gray-500"
						>
							<path
								fill-rule="evenodd"
								d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
								clip-rule="evenodd"
							/>
						</svg>
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
				<XMark className={'size-4'} />
			</button>
		</div>
	{/each}
</div>
