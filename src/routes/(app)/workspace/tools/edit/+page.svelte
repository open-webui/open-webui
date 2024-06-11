<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getToolById, getTools, updateToolById } from '$lib/apis/tools';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ToolkitEditor from '$lib/components/workspace/Tools/ToolkitEditor.svelte';
	import { tools } from '$lib/stores';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	let tool = null;

	const saveHandler = async (data) => {
		console.log(data);
		const res = await updateToolById(localStorage.token, tool.id, {
			id: data.id,
			name: data.name,
			meta: data.meta,
			content: data.content
		}).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			toast.success('Tool updated successfully');
			tools.set(await getTools(localStorage.token));

			// await goto('/workspace/tools');
		}
	};

	onMount(async () => {
		console.log('mounted');
		const id = $page.url.searchParams.get('id');

		if (id) {
			tool = await getToolById(localStorage.token, id).catch((error) => {
				toast.error(error);
				goto('/workspace/tools');
				return null;
			});

			console.log(tool);
		}
	});
</script>

{#if tool}
	<ToolkitEditor
		edit={true}
		id={tool.id}
		name={tool.name}
		meta={tool.meta}
		content={tool.content}
		on:save={(e) => {
			saveHandler(e.detail);
		}}
	/>
{:else}
	<div class="flex items-center justify-center h-full">
		<div class=" pb-16">
			<Spinner />
		</div>
	</div>
{/if}
