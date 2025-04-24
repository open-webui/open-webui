<script lang="ts">
	import KnowledgeBase from '$lib/components/workspace/Knowledge/KnowledgeBase.svelte';
	import { toast } from 'svelte-sonner';
	import CreateKnowledgeBase from '$lib/components/workspace/Knowledge/CreateKnowledgeBase.svelte';
	import { onMount } from 'svelte';
	import {getKnowledgeById} from '$lib/apis/knowledge';
	import { page } from '$app/stores';

	type Knowledge = {
		id: string;
		name: string;
		description: string;
		data: {
			file_ids: string[];
		};
		files: any[];
	};

	let id = null;
	let knowledge: Knowledge | null = null;
	let initialized = false;

	onMount(async() => {
		id = $page.params.id;
		const res = await getKnowledgeById(localStorage.token, id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			knowledge = res;
		} else {
			goto('/workspace/knowledge');
		}

	})
</script>

<CreateKnowledgeBase edit={true} knowledge={knowledge}/>
