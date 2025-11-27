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

	export let show = false;
	export let size = null;
	export let onSave = () => {};

	const submitHandler = async () => {
		onSave(size);
		show = false;
	};

	onMount(() => {});
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-1.5">
			<h1 class="text-lg font-medium self-center font-primary">
				{$i18n.t('Manage')}
			</h1>
			<button
				class="self-center"
				aria-label={$i18n.t('Close modal')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
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
								<div id="image-compression-size-label" class=" text-xs mb-2">
									{$i18n.t('Image Max Compression Size')}
								</div>

								<div class="p-1 flex-1 flex gap-2">
									<div class=" flex-1">
										<label class="sr-only" for="image-comp-width"
											>{$i18n.t('Image Max Compression Size width')}</label
										>
										<input
											bind:value={size.width}
											type="number"
											aria-labelledby="image-comp-width"
											class="w-full bg-transparent outline-hidden text-center"
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
											bind:value={size.height}
											type="number"
											aria-labelledby="image-comp-height"
											class="w-full bg-transparent outline-hidden text-center"
											min="0"
											placeholder={$i18n.t('Height')}
										/>
									</div>
								</div>
							</div>
						</div>
					</div>

					<div class="flex justify-end text-sm font-medium">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
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
