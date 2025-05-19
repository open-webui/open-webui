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
	import LoadingCover from '$lib/IONOS/components/common/LoadingCover.svelte';
	import MagnifyingGlass from '$lib/IONOS/components/icons/MagnifyingGlass.svelte';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte';
	import KnowledgeList from './KnowledgeList.svelte';
	import EditKnowledge from './EditKnowledge.svelte';
	import CreateKnowledge from './CreateKnowledge.svelte';
	import DialogHeader from '$lib/IONOS/components/common/DialogHeader.svelte';

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
		{$i18n.t('Knowledge', { ns: 'ionos' })} | {$WEBUI_NAME}
	</title>
</svelte:head>

<Dialog
	dialogId="knowledge-manager"
	show={$knowledgeManager}
	class="max-w-[800px] min-h-[300px]"
>
	<DialogHeader
		slot="header"
		title={$i18n.t("Knowledge Management", { ns: 'ionos' })}
		on:close={() => { showKnowlegeManager(false); }}
		dialogId="knowledge-manager"
		class="p-[30px]"
	/>

	<div slot="content" class="p-[30px]">
		{#if loaded}
			<div class="flex pb-5 border-b min-w-[500px]">
				<div class="flex grow">
					<div class="self-center ml-1 mr-3">
						<MagnifyingGlass />
					</div>
					<input
						class="w-full text-sm py-1 rounded-r-xl outline-none bg-transparent placeholder:text-blue-800"
						bind:value={query}
						placeholder={$i18n.t('Search Knowledge', { ns: 'ionos' })}
					/>
				</div>
				<div>
					<Button
						on:click={() => create = true}
						type={ButtonType.secondary}
					>
						{$i18n.t('Create knowledge base', { ns: 'ionos' })}
					</Button>
				</div>
			</div>
			<div class="overflow-y-scroll h-[320px]" >
				<KnowledgeList
					items={filteredItems}
					on:select={select}
				/>
			</div>
			<div class=" text-gray-500 text-xs py-4 border-t">
				ⓘ {$i18n.t("Use '#' in the prompt input to load and include your knowledge.", { ns: 'ionos' })}
			</div>
		{:else}
			<LoadingCover size="20" />
		{/if}
	</div>
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
