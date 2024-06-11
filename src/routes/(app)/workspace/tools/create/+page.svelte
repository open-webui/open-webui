<script>
	import ToolkitEditor from '$lib/components/workspace/Tools/ToolkitEditor.svelte';

	const saveHandler = async (data) => {
		console.log(data);
	};
</script>

<ToolkitEditor
	on:save={(e) => {
		saveHandler(e.detail);
	}}
/>
