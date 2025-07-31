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

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div
				class="flex w-full justify-between items-center text-lg font-medium self-center font-primary"
			>
				<div class=" shrink-0">
					{$i18n.t('Manage Ollama')}
				</div>
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<ManageOllama {urlIdx} />
		</div>
	</div>
</Modal>
