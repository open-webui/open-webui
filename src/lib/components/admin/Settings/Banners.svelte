<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';

	import { getContext, onMount } from 'svelte';
	import { banners as _banners } from '$lib/stores';
	import type { Banner } from '$lib/types';

	import { getBanners, setBanners } from '$lib/apis/configs';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	const i18n: Writable<i18nType> = getContext('i18n');

	export let saveHandler: Function;

	let banners: Banner[] = [];

	onMount(async () => {
		banners = await getBanners(localStorage.token);
	});

	const updateBanners = async () => {
		_banners.set(await setBanners(localStorage.token, banners));
	};
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		updateBanners();
		saveHandler();
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-80 h-full">
		<div class=" space-y-3 pr-1.5">
			<div class="flex w-full justify-between mb-2">
				<div class=" self-center text-sm font-semibold">
					{$i18n.t('Banners')}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					type="button"
					on:click={() => {
						if (banners.length === 0 || banners.at(-1).content !== '') {
							banners = [
								...banners,
								{
									id: uuidv4(),
									type: '',
									title: '',
									content: '',
									dismissible: true,
									timestamp: Math.floor(Date.now() / 1000)
								}
							];
						}
					}}
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
			<div class="flex flex-col space-y-1">
				{#each banners as banner, bannerIdx}
					<div class=" flex justify-between">
						<div class="flex flex-row flex-1 border rounded-xl dark:border-gray-800">
							<select
								class="w-fit capitalize rounded-xl py-2 px-4 text-xs bg-transparent outline-none"
								bind:value={banner.type}
							>
								{#if banner.type == ''}
									<option value="" selected disabled class="text-gray-900">{$i18n.t('Type')}</option
									>
								{/if}
								<option value="info" class="text-gray-900">{$i18n.t('Info')}</option>
								<option value="warning" class="text-gray-900">{$i18n.t('Warning')}</option>
								<option value="error" class="text-gray-900">{$i18n.t('Error')}</option>
								<option value="success" class="text-gray-900">{$i18n.t('Success')}</option>
							</select>

							<input
								class="pr-5 py-1.5 text-xs w-full bg-transparent outline-none"
								placeholder={$i18n.t('Content')}
								bind:value={banner.content}
							/>

							<div class="relative top-1.5 -left-2">
								<Tooltip content="Dismissible" className="flex h-fit items-center">
									<Switch bind:state={banner.dismissible} />
								</Tooltip>
							</div>
						</div>

						<button
							class="px-2"
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
		</div>
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			Save
		</button>
	</div>
</form>
