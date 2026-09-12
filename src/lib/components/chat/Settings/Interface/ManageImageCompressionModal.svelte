<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { settings } from '$lib/stores';

	export let show = false;
	export let size = null;
	export let onSave = () => {};

	const submitHandler = async () => {
		onSave(size);
		show = false;
	};

	onMount(() => {});
</script>

<Modal size="sm" bind:show className="bg-white dark:bg-gray-900 rounded-4xl">
	<div>
		<div class=" flex justify-between text-gray-900 dark:text-white px-4 pt-3 pb-1">
			<h1 class="text-sm font-medium self-center">
				{$i18n.t('Manage')}
			</h1>
			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close modal')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div
			class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 text-gray-600 dark:text-gray-400"
		>
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full px-1"
					on:submit={(e) => {
						e.preventDefault();
						submitHandler();
					}}
				>
					<div>
						<div>
							<div class=" py-0.5 flex flex-col w-full text-sm">
								<div
									id="image-compression-size-label"
									class="mb-2 text-xs text-gray-600 dark:text-gray-400"
								>
									{$i18n.t('Image Max Compression Size')}
								</div>

								<div class="p-1 flex-1 flex gap-2">
									<div class=" flex-1">
										<label class="sr-only" for="image-comp-width"
											>{$i18n.t('Image Max Compression Size width')}</label
										>
										<input
											id="image-comp-width"
											bind:value={size.width}
											type="number"
											class="h-7 w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-center text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500"
											min="0"
											placeholder={$i18n.t('Width')}
										/>
									</div>

									<div class="self-center text-gray-500 dark:text-gray-400">
										<XMark />
									</div>

									<div class="flex-1">
										<label class="sr-only" for="image-comp-height"
											>{$i18n.t('Image Max Compression Size height')}</label
										>
										<input
											id="image-comp-height"
											bind:value={size.height}
											type="number"
											class="h-7 w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-center text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500"
											min="0"
											placeholder={$i18n.t('Height')}
										/>
									</div>
								</div>
							</div>
						</div>
					</div>

					<div class="flex justify-end text-sm font-normal">
						<button
							class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
							type="submit"
						>
							{$i18n.t('Save')}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
