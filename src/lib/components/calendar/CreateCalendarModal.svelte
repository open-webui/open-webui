<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import { createCalendar } from '$lib/apis/calendar';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let name = '';
	let color = '#3b82f6';
	let loading = false;

	const PRESET_COLORS = [
		'#3b82f6', // blue
		'#ef4444', // red
		'#22c55e', // green
		'#f59e0b', // amber
		'#8b5cf6', // violet
		'#ec4899', // pink
		'#06b6d4', // cyan
		'#f97316' // orange
	];

	function reset() {
		name = '';
		color = '#3b82f6';
		loading = false;
	}

	$: if (show) reset();

	const submitHandler = async () => {
		if (!name.trim()) {
			toast.error($i18n.t('Name is required'));
			return;
		}

		loading = true;
		try {
			const result = await createCalendar(localStorage.token, {
				name: name.trim(),
				color
			});
			if (result) {
				toast.success($i18n.t('Calendar created'));
				dispatch('created', result);
				show = false;
			}
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			loading = false;
		}
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<!-- Header -->
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-2">
			<h3 class="text-base font-medium">{$i18n.t('New Calendar')}</h3>
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
			<!-- Name -->
			<div>
				<div class="mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>
				<input
					class="w-full text-sm bg-transparent outline-hidden font-primary placeholder:text-gray-300 dark:placeholder:text-gray-700"
					type="text"
					bind:value={name}
					placeholder={$i18n.t('Calendar name')}
					on:keydown={(e) => {
						if (e.key === 'Enter') submitHandler();
					}}
				/>
			</div>

			<!-- Color -->
			<div>
				<div class="mb-1 text-xs text-gray-500">{$i18n.t('Color')}</div>
				<div class="flex items-center gap-2 flex-wrap">
					{#each PRESET_COLORS as c}
						<button
							class="size-6 rounded-full transition-all border-2 {color === c
								? 'border-gray-800 dark:border-white scale-110'
								: 'border-transparent hover:scale-110'}"
							style="background-color: {c};"
							on:click={() => (color = c)}
							aria-label={c}
						/>
					{/each}

					<label
						class="size-6 rounded-full overflow-hidden cursor-pointer border-2 transition-all {!PRESET_COLORS.includes(
							color
						)
							? 'border-gray-800 dark:border-white scale-110'
							: 'border-transparent hover:scale-110'}"
						style="background-color: {color};"
						title={$i18n.t('Custom color')}
					>
						<input type="color" bind:value={color} class="opacity-0 w-0 h-0 absolute" />
					</label>
				</div>
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
				class="px-3.5 py-1.5 text-sm bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 {loading
					? 'cursor-not-allowed'
					: ''}"
				on:click={submitHandler}
				type="button"
				disabled={loading}
			>
				{$i18n.t('Create')}
				{#if loading}
					<span class="shrink-0"><Spinner /></span>
				{/if}
			</button>
		</div>
	</div>
</Modal>
