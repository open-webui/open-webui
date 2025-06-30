<script>
	import { marked } from 'marked';
	import { replaceTokens, processResponseContent } from '$lib/utils';
	import { user, temporaryChatEnabled } from '$lib/stores';
	import { toast } from 'svelte-sonner';

	import markedExtension from '$lib/utils/marked/extension';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';
	import { parseMcpCommand, type McpCommand } from '$lib/utils/mcp';
	import FileUploadWidget from '../widgets/FileUploadWidget.svelte';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';

	export let id = '';
	export let content;
	export let model = null;
	export let save = false;
	export let preview = false;

	export let sourceIds = [];

	export let onSave = () => {};
	export let onUpdate = () => {};

	export let onPreview = () => {};

	export let onSourceClick = () => {};
	export let onTaskClick = () => {};

	let tokens = [];
	let mcpCommand: McpCommand | null = null;

	const options = {
		throwOnError: false
	};

	marked.use(markedKatexExtension(options));
	marked.use(markedExtension(options));

	const handleFileUpload = async (event: CustomEvent<File>) => {
		const file = event.detail;
		if (!file) return;

		const formData = new FormData();
		formData.append('file', file);
		formData.append('chat_id', id); // Assuming 'id' is the chat_id

		// TODO: Replace with actual API endpoint and error handling
		// This is a placeholder for the backend integration.
		// The actual endpoint might be different and will require backend implementation.
		const targetHost = $temporaryChatEnabled ? `${window.location.protocol}//${window.location.host}` : '';


		try {
			const response = await fetch(`${targetHost}/mcp/upload`, {
				method: 'POST',
				body: formData
				// Add headers if needed, e.g., Authorization
			});

			if (response.ok) {
				const result = await response.json();
				toast.success(`File uploaded successfully: ${result.filename}`);
				// Potentially, send a message back to the chat indicating success
			} else {
				const errorText = await response.text();
				toast.error(`File upload failed: ${response.statusText} - ${errorText}`);
			}
		} catch (error) {
			console.error('Error uploading file:', error);
			toast.error(`File upload failed: ${error.message}`);
		}
	};

	$: (async () => {
		if (content) {
			mcpCommand = parseMcpCommand(content);
			if (!mcpCommand) {
				tokens = marked.lexer(
					replaceTokens(processResponseContent(content), sourceIds, model?.name, $user?.name)
				);
			}
		}
	})();
</script>

{#key id}
	{#if mcpCommand}
		<FileUploadWidget on:upload={handleFileUpload} />
	{:else}
		<MarkdownTokens
			{tokens}
			{id}
			{save}
			{preview}
			{onTaskClick}
			{onSourceClick}
			{onSave}
			{onUpdate}
			{onPreview}
		/>
	{/if}
{/key}
