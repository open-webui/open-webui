<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import CloseIcon from '$lib/components/icons/CloseIcon.svelte';
	import { showLibrary, company } from '$lib/stores';
	import { getModels } from '$lib/apis/models';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import BookmarkedIcon from '$lib/components/icons/BookmarkedIcon.svelte';
    import { goto } from '$app/navigation';

	const i18n = getContext('i18n');
	let models = null;

    export let selectedChatId = null;

	const getWorkspaceModels = async () => {
		models = await getModels(localStorage.token);
	};

	$: if ($showLibrary) {
		getWorkspaceModels();
	}
</script>

{#if $showLibrary}
	<div
		class="fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-lightGray-700/40 dark:bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			showLibrary.set(!$showLibrary);
		}}
	/>
{/if}

<div
	id="library-sidebar"
	class="pl-6 h-screen max-h-[100dvh] min-h-screen select-none {$showLibrary
		? 'md:relative w-[400px] max-w-[400px]'
		: 'translate-x-[400px] w-[0px]'} 
		transition-width duration-200 ease-in-out flex-shrink-0 bg-lightGray-200 text-gayLight-100 dark:bg-customGray-800 dark:text-gray-200 text-sm fixed z-50 top-0 right-0 bottom-0 overflow-x-hidden
        "
	data-state={$showLibrary}
>
	<div class="flex items-center justify-between pt-6 pr-6 pb-6">
		<p>{$i18n.t('Assistants')}</p>
		<button on:click={() => showLibrary.set(!$showLibrary)}><CloseIcon /></button>
	</div>
	{#if !models}
		<div class=" h-full w-full flex justify-center items-center">
			<Spinner />
		</div>
	{:else}
		<div class="flex gap-5 overflow-x-scroll py-3">
			{#each models as model}
				<Tooltip placement="bottom" content={model?.name + '. ' + model?.meta?.description}>
					<button on:click={async () => {
						selectedChatId = null;
						await goto(`/?models=${encodeURIComponent(model.id)}`);
						const newChatButton = document.getElementById('new-chat-button');
						setTimeout(() => {
							newChatButton?.click();
						}, 0);
					}} class="block w-[4rem] h-[4rem] relative">
						{#if model?.bookmarked}
							<div
								class="flex justify-center items-center absolute w-7 h-7 -right-3.5 -top-3.5 rounded-lg dark:bg-customGray-900 border dark:border-customGray-700"
							>
								<BookmarkedIcon />
							</div>
						{/if}
						<img
							class="rounded-md"
							src={model?.meta?.profile_image_url
								? model?.meta?.profile_image_url
								: $company?.profile_image_url}
							alt=""
						/>
                    </button>
				</Tooltip>
			{/each}
		</div>
	{/if}
</div>
