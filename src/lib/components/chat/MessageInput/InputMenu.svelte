<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, onMount, tick } from 'svelte';

	import { config, user, tools as _tools, mobile } from '$lib/stores';
	import { createPicker } from '$lib/utils/google-drive-picker';
	import { getTools } from '$lib/apis/tools';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentArrowUpSolid from '$lib/components/icons/DocumentArrowUpSolid.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAltSolid from '$lib/components/icons/GlobeAltSolid.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import CameraSolid from '$lib/components/icons/CameraSolid.svelte';
	import PhotoSolid from '$lib/components/icons/PhotoSolid.svelte';

	const i18n = getContext('i18n');

	export let screenCaptureHandler: Function;
	export let uploadFilesHandler: Function;
	export let uploadGoogleDriveHandler: Function;

	export let selectedToolIds: string[] = [];

	export let webSearchEnabled: boolean;
	export let imageGenerationEnabled: boolean;

	export let onClose: Function;

	let tools = {};
	let show = false;

	let showImageGeneration = false;

	$: showImageGeneration =
		$config?.features?.enable_image_generation &&
		($user.role === 'admin' || $user?.permissions?.features?.image_generation);

	let showWebSearch = false;

	$: showWebSearch =
		$config?.features?.enable_web_search &&
		($user.role === 'admin' || $user?.permissions?.features?.web_search);

	$: if (show) {
		init();
	}

	const init = async () => {
		if ($_tools === null) {
			await _tools.set(await getTools(localStorage.token));
		}

		tools = $_tools.reduce((a, tool, i, arr) => {
			a[tool.id] = {
				name: tool.name,
				description: tool.meta.description,
				enabled: selectedToolIds.includes(tool.id)
			};
			return a;
		}, {});
	};
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[220px] rounded-xl px-1 py-1  border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow"
			sideOffset={15}
			alignOffset={-8}
			side="top"
			align="start"
			transition={flyAndScale}
		>
			{#if Object.keys(tools).length > 0}
				<div class="  max-h-28 overflow-y-auto scrollbar-hidden">
					{#each Object.keys(tools) as toolId}
						<button
							class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer rounded-xl"
							on:click={() => {
								tools[toolId].enabled = !tools[toolId].enabled;
							}}
						>
							<div class="flex-1 truncate">
								<Tooltip
									content={tools[toolId]?.description ?? ''}
									placement="top-start"
									className="flex flex-1 gap-2 items-center"
								>
									<div class="flex-shrink-0">
										<WrenchSolid />
									</div>

									<div class=" truncate">{tools[toolId].name}</div>
								</Tooltip>
							</div>

							<div class=" flex-shrink-0">
								<Switch
									state={tools[toolId].enabled}
									on:change={async (e) => {
										const state = e.detail;
										await tick();
										if (state) {
											selectedToolIds = [...selectedToolIds, toolId];
										} else {
											selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
										}
									}}
								/>
							</div>
						</button>
					{/each}
				</div>

				<hr class="border-black/5 dark:border-white/5 my-1" />
			{/if}

			{#if showImageGeneration}
				<button
					class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer rounded-xl"
					on:click={() => {
						imageGenerationEnabled = !imageGenerationEnabled;
					}}
				>
					<div class="flex-1 flex items-center gap-2">
						<PhotoSolid />
						<div class=" line-clamp-1">{$i18n.t('Image')}</div>
					</div>

					<Switch state={imageGenerationEnabled} />
				</button>
			{/if}

			{#if showWebSearch}
				<button
					class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer rounded-xl"
					on:click={() => {
						webSearchEnabled = !webSearchEnabled;
					}}
				>
					<div class="flex-1 flex items-center gap-2">
						<GlobeAltSolid />
						<div class=" line-clamp-1">{$i18n.t('Web Search')}</div>
					</div>

					<Switch state={webSearchEnabled} />
				</button>
			{/if}

			{#if showImageGeneration || showWebSearch}
				<hr class="border-black/5 dark:border-white/5 my-1" />
			{/if}

			{#if !$mobile}
				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800  rounded-xl"
					on:click={() => {
						screenCaptureHandler();
					}}
				>
					<CameraSolid />
					<div class=" line-clamp-1">{$i18n.t('Capture')}</div>
				</DropdownMenu.Item>
			{/if}

			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
				on:click={() => {
					uploadFilesHandler();
				}}
			>
				<DocumentArrowUpSolid />
				<div class="line-clamp-1">{$i18n.t('Upload Files')}</div>
			</DropdownMenu.Item>

			{#if $config?.features?.enable_google_drive_integration}
				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						uploadGoogleDriveHandler();
					}}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 87.3 78" class="w-5 h-5">
						<path
							d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z"
							fill="#0066da"
						/>
						<path
							d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z"
							fill="#00ac47"
						/>
						<path
							d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z"
							fill="#ea4335"
						/>
						<path
							d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z"
							fill="#00832d"
						/>
						<path
							d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z"
							fill="#2684fc"
						/>
						<path
							d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z"
							fill="#ffba00"
						/>
					</svg>
					<div class="line-clamp-1">{$i18n.t('Google Drive')}</div>
				</DropdownMenu.Item>
			{/if}
		</DropdownMenu.Content>
	</div>
</Dropdown>
