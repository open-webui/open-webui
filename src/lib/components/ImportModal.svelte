<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { extractFrontmatter } from '$lib/utils';

	export let show = false;

	export let onImport = (e) => {};
	export let onClose = () => {};

	export let loadUrlHandler: Function = () => {};
	export let successMessage: string = '';

	let loading = false;
	let url = '';

	const submitHandler = async () => {
		loading = true;

		if (!url) {
			toast.error($i18n.t('Please enter a valid URL'));
			loading = false;
			return;
		}

		const res = await loadUrlHandler(url).catch((err) => {
			toast.error(`${err}`);
			loading = false;
			return null;
		});

		if (res) {
			if (!successMessage) {
				successMessage = $i18n.t('Function imported successfully');
			}

			toast.success(successMessage);

			let func = res;
			func.id = func.id || func.name.replace(/\s+/g, '_').toLowerCase();

			const frontmatter = extractFrontmatter(res.content); // Ensure frontmatter is extracted

			if (frontmatter?.title) {
				func.name = frontmatter.title;
			}

			func.meta = {
				...(func.meta ?? {}),
				description: frontmatter?.description ?? func.name
			};

			onImport(func);
			show = false;
		}
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">{$i18n.t('Import')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-3 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="px-1">
						<div class="flex flex-col w-full">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('URL')}</div>

							<div class="flex-1">
								<input
									class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
									type="url"
									bind:value={url}
									placeholder={$i18n.t('Enter the URL to import')}
									required
								/>

								<!-- $i18n.t('Enter the URL of the function to import') -->
							</div>
						</div>
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Import')}

							{#if loading}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
