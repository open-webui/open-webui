<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import ManageOllama from '../Models/Manage/ManageOllama.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let urlIdx: number | null = null;
</script>

<Modal
	ariaLabel={$i18n.t('Manage Ollama')}
	size="sm"
	bind:show
	className="bg-white dark:bg-base-900 rounded-4xl"
>
	<div>
		<div class=" flex justify-between dark:text-base-100 px-4 pt-3 pb-1">
			<div class="flex w-full justify-between items-center text-sm font-medium self-center">
				<div class=" shrink-0">
					{$i18n.t('Manage Ollama')}
				</div>
			</div>
			<button
				aria-label={$i18n.t('Close')}
				class="self-center rounded-lg py-1 text-base-500 transition hover:text-base-700 dark:text-base-400 dark:hover:text-base-200 px-0"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-base-200">
			<ManageOllama {urlIdx} />
		</div>
	</div>
</Modal>
