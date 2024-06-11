<script>
	import { goto } from '$app/navigation';
	import { createNewTool, getTools } from '$lib/apis/tools';
	import ToolkitEditor from '$lib/components/workspace/Tools/ToolkitEditor.svelte';
	import { tools } from '$lib/stores';
	import { toast } from 'svelte-sonner';

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
</script>

<ToolkitEditor
	on:save={(e) => {
		saveHandler(e.detail);
	}}
/>
