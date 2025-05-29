<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import CloseIcon from '$lib/components/icons/CloseIcon.svelte';
	import { showLibrary, company } from '$lib/stores';
	import { getModels } from '$lib/apis/models';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import BookmarkedIcon from '$lib/components/icons/BookmarkedIcon.svelte';
	import { goto } from '$app/navigation';
	import { getPromptList } from '$lib/apis/prompts';
	import Accordeon from '$lib/components/chat/Settings/CompanySettings/Accordeon.svelte';
	import { get } from 'svelte/store';
	import { confirmPromptFn, user } from '$lib/stores';
	import PublicIcon from '$lib/components/icons/PublicIcon.svelte';
	import PrivateIcon from '$lib/components/icons/PrivateIcon.svelte';
	import GroupIcon from '$lib/components/icons/GroupIcon.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	const i18n = getContext('i18n');
	let models = null;
	let prompts = null;

	let accessFilter = 'all';

	export let selectedChatId = null;

	const getWorkspaceModels = async () => {
		models = await getModels(localStorage.token);
	};

	const initPrompts = async () => {
		prompts = await getPromptList(localStorage.token);
	};

	$: if ($showLibrary) {
		getWorkspaceModels();
		initPrompts();
	}

	let filteredItems = [];

	let taggedPrompts = {};

	const tagColors = ['#272A6A', '#044B49', '#2F074F', '#27456A', '#0C2E18', '#47074F', '#6A2738'];

	$: {
		if (prompts) {
			filteredItems = prompts?.filter((p) => {
				const isPublic = p.access_control === null && !p.prebuilt;
				const isPrivate = p?.user_id === $user?.id;
				const isPrebuilt = p.prebuilt;

				const accessMatch =
					accessFilter === 'all' ||
					(accessFilter === 'public' && isPublic) ||
					(accessFilter === 'private' && isPrivate) ||
					(accessFilter === 'pre-built' && isPrebuilt);

				return accessMatch;
			});
		}
	}

	$: if (filteredItems) {
		taggedPrompts = {};

		for (const prompt of filteredItems) {
			const tagNames = prompt.meta?.tags?.map((t) => t.name.toLowerCase()) || [];

			for (const tag of tagNames) {
				if (!taggedPrompts[tag]) {
					taggedPrompts[tag] = [];
				}
				taggedPrompts[tag].push(prompt);
			}
		}
	}
	const onPromptClick = (prompt) => {
		const fn = get(confirmPromptFn);
		if (fn) {
			fn(prompt);
		}
	};
    let isDragging = false;
	function dragScroll(node: HTMLElement) {
		let isDown = false;

		function onMouseDown(e: MouseEvent) {
			isDown = true;
            isDragging = true;
			node.style.cursor = 'grabbing';
			node.dataset.scrollLeft = String(node.scrollLeft);
			node.dataset.startX = String(e.pageX);
			window.addEventListener('mousemove', onMouseMove);
			window.addEventListener('mouseup', onMouseUp);
		}

		function onMouseMove(e: MouseEvent) {
			if (!isDown) return;
			const startX = Number(node.dataset.startX);
			const scrollLeft = Number(node.dataset.scrollLeft);
			node.scrollLeft = scrollLeft - (e.pageX - startX);
		}

		function onMouseUp() {
			isDown = false;
            isDragging = false;
			node.style.cursor = 'grab';
			window.removeEventListener('mousemove', onMouseMove);
			window.removeEventListener('mouseup', onMouseUp);
		}

		node.addEventListener('mousedown', onMouseDown);

		return {
			destroy() {
				node.removeEventListener('mousedown', onMouseDown);
			}
		};
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
		? 'md:relative w-[325px] max-w-[325px] sm:w-[400px] sm:max-w-[400px]'
		: 'translate-x-[325px] sm:translate-x-[400px] w-[0px]'} 
		transition-width duration-200 ease-in-out flex-shrink-0 bg-lightGray-200 text-gayLight-100 dark:bg-customGray-950 dark:text-gray-200 text-sm fixed z-50 top-0 right-0 bottom-0 overflow-x-hidden
        "
	data-state={$showLibrary}
>
	<div class="flex items-center justify-between pt-6 pr-6 pb-6">
		<p class="text-lightGray-100 dark:text-white text-base">{$i18n.t('Assistants')}</p>
		<button on:click={() => showLibrary.set(!$showLibrary)}><CloseIcon /></button>
	</div>
	{#if !models || !prompts}
		<div class=" h-full w-full flex justify-center items-center">
			<Spinner />
		</div>
	{:else}
		<div class="sticky top-0 z-10 pb-3">
			<div
				use:dragScroll
				class="cursor-grab flex gap-5 overflow-x-scroll py-3.5 assistants-scrollbar"
			>
				{#each models as model}
					<Tooltip className="tooltip" placement="bottom" content={isDragging ? '' : model?.name + '. ' + model?.meta?.description}>
						<button
							on:click={async () => {
								selectedChatId = null;
								await goto(`/?models=${encodeURIComponent(model.id)}`);
								const newChatButton = document.getElementById('new-chat-button');
								setTimeout(() => {
									newChatButton?.click();
								}, 0);
							}}
							class="block w-[4rem] h-[4rem] relative"
						>
							{#if model?.bookmarked}
								<div
									class="flex justify-center items-center absolute w-7 h-7 -right-3.5 -top-3.5 rounded-lg bg-lightGray-700 dark:bg-customGray-900 border border-lightGray-300 dark:border-customGray-700"
								>
									<BookmarkedIcon />
								</div>
							{/if}
							<img
								class="rounded-md"
								src={model?.meta?.profile_image_url
									? model?.meta?.profile_image_url
									: $company?.profile_image_url}
								draggable="false"
								alt={model?.name}
							/>
						</button>
					</Tooltip>
				{/each}
			</div>
		</div>
		<p class="text-lightGray-100 dark:text-white text-base mb-3">{$i18n.t('Prompts')}</p>
		<div class="flex justify-between items-center mb-4">
			<div class="flex bg-lightGray-700 dark:bg-customGray-800 rounded-md flex-shrink-0">
				<button
					on:click={() => (accessFilter = 'all')}
					class={`${accessFilter === 'all' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-2 md:px-[18px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('All')}</button
				>
				<button
					on:click={() => (accessFilter = 'private')}
					class={`${accessFilter === 'private' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-2 md:px-[18px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('My Prompts')}</button
				>
				<button
					on:click={() => (accessFilter = 'public')}
					class={`${accessFilter === 'public' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-2 md:px-[18px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('Public')}</button
				>
				<button
					on:click={() => (accessFilter = 'pre-built')}
					class={`${accessFilter === 'pre-built' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-2 md:px-[18px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('Pre-built')}</button
				>
			</div>
			<button
				class="flex justify-center items-center w-[42px] h-[32px] rounded-lg mr-1 border border-lightGray-400 dark:border-customGray-700 hover:bg-lightGray-700 dark:hover:bg-customGray-950 dark:hover:text-white transition"
				type="button"
			>
				<Search className="size-3.5" />
			</button>
		</div>
		<div class="prompt-scrollbar overflow-y-auto pr-6" style="max-height: calc(100dvh - 17rem);">
			<div class="container">
				{#each Object.keys(taggedPrompts) as tag, i}
					<Accordeon
						hideBorder={true}
						tagColor={tagColors[i % tagColors?.length]}
						titleClassName={`text-xs text-white rounded-lg px-2 py-1`}
						id={tag}
					>
						<span class="capitalize font-medium" slot="title">{tag} </span>
						{#each taggedPrompts[tag] as prompt}
							<div class="flex items-center py-1">
								<div class="w-4 shrink-0">
									{#if prompt?.bookmarked}
										<BookmarkedIcon className="size-3" />
									{/if}
								</div>
								{#if prompt?.access_control === null}
									<div class="shrink-0 mr-[6px]"><PublicIcon className="size-3" /></div>
								{:else if prompt?.access_control?.read?.group_ids?.length > 0 || prompt?.access_control?.write?.group_ids?.length > 0}
									<div class="shrink-0 mr-[6px]"><GroupIcon className="size-3" /></div>
								{:else}
									<div class="shrink-0 mr-[6px]"><PrivateIcon className="size-3" /></div>
								{/if}
								<div
									class="line-clamp-1 font-medium text-sm text-lightGray-100 dark:text-customGray-100 cursor-pointer"
									on:click={() => onPromptClick(prompt)}
								>
									{prompt?.title}. {prompt?.description}
								</div>
							</div>
						{/each}
					</Accordeon>
				{/each}
			</div>
		</div>
	{/if}
</div>
