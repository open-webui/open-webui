<script>
	import { goto } from '$app/navigation';
	import { createNewTool, getTools } from '$lib/apis/tools';
	import ToolkitEditor from '$lib/components/workspace/Tools/ToolkitEditor.svelte';
	import { tools } from '$lib/stores';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	let tool = null;

	const saveHandler = async (data) => {
		console.log(data);
		const res = await createNewTool(localStorage.token, {
			id: data.id,
			name: data.name,
			meta: data.meta,
			content: data.content
		}).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			toast.success('Tool created successfully');
			tools.set(await getTools(localStorage.token));

			await goto('/workspace/tools');
		}
	};

	onMount(() => {
		console.log('mounted');

		if (sessionStorage.tool) {
			tool = JSON.parse(sessionStorage.tool);
			sessionStorage.removeItem('tool');
		}
	});
</script>

<ToolkitEditor
	id={tool?.id ?? ''}
	name={tool?.name ?? ''}
	meta={tool?.meta ?? { description: '' }}
	content={tool?.content ?? ''}
	on:save={(e) => {
		saveHandler(e.detail);
	}}
/>
