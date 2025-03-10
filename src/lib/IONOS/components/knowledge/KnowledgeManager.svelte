<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import type {
		Knowledge,
		KnowledgeId,
	} from '$lib/apis/knowledge/types';
	import { getContext, onMount } from 'svelte';
	import Fuse from 'fuse.js';
	import { knowledge } from '$lib/stores';
	import { getKnowledgeBaseList } from '$lib/apis/knowledge';
	import { WEBUI_NAME } from '$lib/stores';
	import { knowledgeManager, showKnowlegeManager } from '$lib/IONOS/stores/dialogs';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';
	import KnowledgeList from './KnowledgeList.svelte';
	import EditKnowledge from './EditKnowledge.svelte';
	import CreateKnowledge from './CreateKnowledge.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');

	let loaded = false;

	let query = '';
	let fuse: Fuse<Knowledge>|null = null;

	let knowledgeBases: Knowledge[] = [];
	let filteredItems: Knowledge[] = [];
	let knowledgeBeingEdited:Knowledge|null = null;
	let create = false;

	$: if (knowledgeBases) {
		fuse = new Fuse(knowledgeBases, {
			keys: ['name', 'description']
		});
	}

	$: if (fuse) {
		filteredItems = query
			? fuse.search(query).map((e) => {
					return e.item;
				})
			: knowledgeBases;
	}

	function select({ detail: knowledgeId }: { detail: KnowledgeId }): void {
		knowledgeBeingEdited = knowledgeBases.find(({ id }) => id == knowledgeId) ?? null;
	}

	async function load() {
		loaded = false;
		knowledgeBases = await getKnowledgeBaseList(localStorage.token);
		loaded = true;
	}

	async function onKnowledgeDeleted(): Promise<void> {
		await load();
		knowledgeBeingEdited = null;
	}

	async function onEditClose(): Promise<void> {
		await load();
		knowledgeBeingEdited = null;
	}

	async function onKnowledgeCreated(): Promise<void> {
		await load();
		create = false;
	}

	function onCloseManager() {
		// @ts-expect-error Argument of type 'Knowledge[]' is not assignable to parameter of type 'Document[]'.
		knowledge.set(knowledgeBases);
		create = false;
	}

	onMount(async () => {
		load();
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Knowledge')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<Dialog
	title={$i18n.t("Knowledge Management", { ns: 'ionos' })}
	dialogId="knowledge-manager"
	on:close={() => { showKnowlegeManager(false); }}
	show={$knowledgeManager}
>
	{#if loaded}
		<div class="flex py-4 border-b min-w-[500px]">
			<div class="flex grow">
				<div class="self-center ml-1 mr-3">
					<Search className="size-5" />
				</div>
				<input
					class="w-full text-sm py-1 rounded-r-xl outline-none bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Knowledge')}
				/>
			</div>
			<div>
				<button
					class="px-4 py-1 border-2 border-sky-900 bg-white-500 hover:bg-sky-800 text-black hover:text-white transition rounded-3xl"
					on:click={() => create = true}
				>
					{$i18n.t('Create knowledge base', { ns: 'ionos' })}
				</button>
			</div>
		</div>

		<div class="overflow-y-scroll h-[320px]">
			<KnowledgeList
				items={filteredItems}
				on:select={select}
			/>
		</div>

		<div class=" text-gray-500 text-xs py-4 border-t">
			ⓘ {$i18n.t("Use '#' in the prompt input to load and include your knowledge.")}
		</div>
	{:else}
		<div class="w-full h-full flex justify-center items-center">
			<Spinner />
		</div>
	{/if}
</Dialog>

{#if knowledgeBeingEdited}
	<EditKnowledge
		knowledge={knowledgeBeingEdited}
		on:deleted={onKnowledgeDeleted}
		on:close={onEditClose}
	/>
{/if}

{#if create}
	<CreateKnowledge
		show={true}
		on:created={onKnowledgeCreated}
		on:close={onCloseManager}
	/>
{/if}
