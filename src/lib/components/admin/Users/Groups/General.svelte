<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { getSharepointTenants, getSharepointSites } from '$lib/apis/sharepoint';
	import type { TenantInfo, SiteInfo } from '$lib/apis/sharepoint';

	const i18n = getContext('i18n');

	export let name = '';
	export let color = '';
	export let description = '';
	export let data = {};

	export let edit = false;
	export let onDelete: Function = () => {};

	// SharePoint state
	let sharepointSectionOpen = false;
	let sharepointTenants: TenantInfo[] = [];
	let sharepointSites: SiteInfo[] = [];
	let sharepointLoading = false;
	let sharepointConfigured = false;
	let siteSearchQuery = '';

	$: allowedSites = (data?.sharepoint?.allowed_sites as string[]) ?? [];
	$: filteredSites = sharepointSites.filter((site) =>
		site.display_name.toLowerCase().includes(siteSearchQuery.toLowerCase())
	);

	const loadSharepointConfig = async () => {
		sharepointLoading = true;
		try {
			sharepointTenants = await getSharepointTenants(localStorage.token);
			sharepointConfigured = sharepointTenants.length > 0;
			if (sharepointConfigured && sharepointTenants.length > 0) {
				sharepointSites = await getSharepointSites(localStorage.token, sharepointTenants[0].id);
			}
		} catch (err) {
			console.error('Failed to load SharePoint config:', err);
			sharepointConfigured = false;
		} finally {
			sharepointLoading = false;
		}
	};

	const toggleSiteAccess = (siteName: string) => {
		const current = [...allowedSites];
		if (current.includes(siteName)) {
			data = {
				...data,
				sharepoint: {
					...(data?.sharepoint ?? {}),
					allowed_sites: current.filter((s) => s !== siteName)
				}
			};
		} else {
			data = {
				...data,
				sharepoint: { ...(data?.sharepoint ?? {}), allowed_sites: [...current, siteName] }
			};
		}
	};

	const clearAllSites = () => {
		data = {
			...data,
			sharepoint: { ...(data?.sharepoint ?? {}), allowed_sites: [] }
		};
	};

	onMount(() => {
		loadSharepointConfig();
	});
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

<!-- SharePoint Access Section -->
{#if sharepointConfigured}
	<hr class="border-gray-50 dark:border-gray-850/30 my-1" />

	<div class="flex flex-col w-full mt-2">
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<div
			class="flex items-center justify-between cursor-pointer select-none group"
			on:click={() => {
				sharepointSectionOpen = !sharepointSectionOpen;
			}}
		>
			<div class="flex items-center gap-2">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="size-4 text-accent-500 dark:text-accent-400"
				>
					<path d="M4 22h14a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v4" />
					<path d="M14 2v5h5" />
					<path d="m3 15 2 2 4-4" />
				</svg>
				<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
					{$i18n.t('SharePoint Access')}
				</span>
				{#if allowedSites.length > 0}
					<span
						class="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-accent-500/10 text-accent-600 dark:text-accent-400"
					>
						{allowedSites.length}
						{allowedSites.length === 1 ? $i18n.t('site') : $i18n.t('sites')}
					</span>
				{/if}
			</div>
			<div
				class="text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-transform duration-200"
				class:rotate-180={sharepointSectionOpen}
			>
				<ChevronDown className="size-4" strokeWidth="2" />
			</div>
		</div>

		{#if sharepointSectionOpen}
			<div class="mt-3 space-y-3" transition:slide={{ duration: 200, easing: quintOut }}>
				<div class="text-xs text-gray-400 dark:text-gray-500">
					{$i18n.t(
						'Select which SharePoint sites members of this group can access. Sites are merged with any user-level access.'
					)}
				</div>

				<!-- Site selection -->
				<div class="rounded-lg border border-gray-150 dark:border-gray-800 overflow-hidden">
					<!-- Search -->
					{#if sharepointSites.length > 5}
						<div class="px-3 py-2 border-b border-gray-100 dark:border-gray-800">
							<input
								type="text"
								class="w-full text-sm bg-transparent outline-hidden placeholder-gray-400 dark:placeholder-gray-500"
								placeholder={$i18n.t('Search sites...')}
								bind:value={siteSearchQuery}
							/>
						</div>
					{/if}

					<!-- Site list -->
					<div class="max-h-48 overflow-y-auto">
						{#if sharepointLoading}
							<div class="flex items-center justify-center py-6 text-sm text-gray-400">
								<svg
									class="animate-spin size-4 mr-2"
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
								>
									<circle
										class="opacity-25"
										cx="12"
										cy="12"
										r="10"
										stroke="currentColor"
										stroke-width="4"
									/>
									<path
										class="opacity-75"
										fill="currentColor"
										d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
									/>
								</svg>
								{$i18n.t('Loading sites...')}
							</div>
						{:else if filteredSites.length === 0}
							<div class="py-6 text-center text-sm text-gray-400 dark:text-gray-500">
								{siteSearchQuery
									? $i18n.t('No sites match your search')
									: $i18n.t('No sites available')}
							</div>
						{:else}
							{#each filteredSites as site (site.id)}
								{@const isSelected = allowedSites.includes(site.display_name)}
								<!-- svelte-ignore a11y-no-static-element-interactions -->
								<!-- svelte-ignore a11y-click-events-have-key-events -->
								<div
									class="flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors
										{isSelected
										? 'bg-accent-500/5 dark:bg-accent-400/5'
										: 'hover:bg-gray-50 dark:hover:bg-gray-900/30'}"
									on:click={() => toggleSiteAccess(site.display_name)}
								>
									<div
										class="flex items-center justify-center size-4 rounded border transition-colors flex-shrink-0
											{isSelected
											? 'bg-accent-500 dark:bg-accent-400 border-accent-500 dark:border-accent-400'
											: 'border-gray-300 dark:border-gray-600'}"
									>
										{#if isSelected}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												fill="none"
												stroke="white"
												stroke-width="3"
												stroke-linecap="round"
												stroke-linejoin="round"
												class="size-3"
											>
												<polyline points="20 6 9 17 4 12" />
											</svg>
										{/if}
									</div>
									<div class="flex flex-col min-w-0">
										<span
											class="text-sm truncate {isSelected
												? 'text-gray-800 dark:text-gray-200 font-medium'
												: 'text-gray-600 dark:text-gray-400'}"
										>
											{site.display_name}
										</span>
									</div>
								</div>
							{/each}
						{/if}
					</div>

					<!-- Footer summary -->
					{#if allowedSites.length > 0}
						<div
							class="px-3 py-2 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/30"
						>
							<div class="flex items-center justify-between">
								<span class="text-xs text-gray-500 dark:text-gray-400">
									{allowedSites.length}
									{allowedSites.length === 1 ? $i18n.t('site selected') : $i18n.t('sites selected')}
								</span>
								<!-- svelte-ignore a11y-no-static-element-interactions -->
								<!-- svelte-ignore a11y-click-events-have-key-events -->
								<span
									class="text-xs text-accent-500 dark:text-accent-400 cursor-pointer hover:underline"
									on:click|stopPropagation={() => {
										clearAllSites();
									}}
								>
									{$i18n.t('Clear all')}
								</span>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if}

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
