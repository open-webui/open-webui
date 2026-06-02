<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let name = '';

	$: if (show) {
		name = '';
	}

	const submitHandler = () => {
		if (!name.trim()) {
			toast.error($i18n.t('Name is required'));
			return;
		}

		dispatch('submit', { name: name.trim() });
		show = false;
		name = '';
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<!-- Header -->
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-2">
			<h3 class="text-base font-medium">{$i18n.t('New Directory')}</h3>
			<button
				class="self-center shrink-0 ml-2"
				aria-label={$i18n.t('Close')}
				on:click={() => (show = false)}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<!-- Form -->
		<div class="px-5 pb-2 flex flex-col gap-3">
			<div>
				<div class="mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>
				<input
					class="w-full text-sm bg-transparent outline-hidden font-primary placeholder:text-gray-300 dark:placeholder:text-gray-700"
					type="text"
					bind:value={name}
					placeholder={$i18n.t('Directory name')}
					on:keydown={(e) => {
						if (e.key === 'Enter') submitHandler();
					}}
				/>
			</div>
		</div>

		<!-- Bottom toolbar -->
		<div class="flex items-center justify-end px-4 pb-3.5 pt-2 gap-2">
			<button
				class="px-3 py-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 transition"
				type="button"
				on:click={() => (show = false)}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				class="px-3.5 py-1.5 text-sm bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
				on:click={submitHandler}
				type="button"
			>
				{$i18n.t('Create')}
			</button>
		</div>
	</div>
</Modal>
