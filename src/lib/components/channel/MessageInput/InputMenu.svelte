<script lang="ts">
	import { fly } from 'svelte/transition';
	import { getContext, onMount, tick } from 'svelte';

	import { knowledge } from '$lib/stores';
	import { getKnowledgeBases } from '$lib/apis/knowledge';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Camera from '$lib/components/icons/Camera.svelte';
	import Clip from '$lib/components/icons/Clip.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import Knowledge from '$lib/components/chat/MessageInput/InputMenu/Knowledge.svelte';

	const i18n = getContext('i18n');

	export let screenCaptureHandler: Function;
	export let uploadFilesHandler: Function;
	export let knowledgeHandler: Function = () => {};
	export let onClose: Function = () => {};

	let show = false;
	let tab = '';

	const init = async () => {
		if ($knowledge === null) {
			knowledge.set(await getKnowledgeBases(localStorage.token));
		}
	};

	$: if (show) {
		init();
	} else {
		tab = ''; // Reset tab when dropdown closes
	}

	const onSelect = (item) => {
		knowledgeHandler(item);
		show = false;
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
		<div
			class="w-full max-w-70 rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-999 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-72 overflow-y-auto scrollbar-thin transition"
		>
			{#if tab === ''}
				<div in:fly={{ x: -20, duration: 150 }}>
					<button
						class="select-none flex w-full gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl"
						type="button"
						on:click={() => {
							uploadFilesHandler();
							show = false;
						}}
					>
						<Clip />
						<div class="line-clamp-1">{$i18n.t('Upload Files')}</div>
					</button>

					<button
						class="select-none flex w-full gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl"
						type="button"
						on:click={() => {
							screenCaptureHandler();
							show = false;
						}}
					>
						<Camera />
						<div class=" line-clamp-1">{$i18n.t('Capture')}</div>
					</button>

					{#if ($knowledge ?? []).length > 0}
						<button
							class="flex gap-2 w-full items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl"
							type="button"
							on:click={() => {
								tab = 'knowledge';
							}}
						>
							<Database />

							<div class="flex items-center w-full justify-between">
								<div class="line-clamp-1">{$i18n.t('Attach Knowledge')}</div>
								<div class="text-gray-500">
									<ChevronRight />
								</div>
							</div>
						</button>
					{/if}
				</div>
			{:else if tab === 'knowledge'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						type="button"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />
						<div class="flex items-center w-full justify-between">
							<div>{$i18n.t('Knowledge')}</div>
						</div>
					</button>

					<Knowledge {onSelect} />
				</div>
			{/if}
		</div>
	</div>
</Dropdown>
