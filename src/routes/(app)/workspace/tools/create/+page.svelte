<script lang="ts">
	import { goto } from '$app/navigation';
	import { createNewTool, getTools } from '$lib/apis/tools';
	import ToolkitEditor from '$lib/components/workspace/Tools/ToolkitEditor.svelte';
	import { WEBUI_VERSION } from '$lib/constants';
	import { tools } from '$lib/stores';
	import { compareVersion, extractFrontmatter } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let mounted = false;
	let clone = false;

	interface Tool {
		id?: string;
		name?: string;
		meta?: {
			description: string;
		};
		content?: string;
	}

	interface Manifest {
		required_open_webui_version?: string;
	}

	let tool: Tool | null = null;

	const saveHandler = async (data: {
		id: string;
		name: string;
		meta: { description: string };
		content: string;
		access_control: null | undefined;
	}) => {
		console.log(data);

		const manifest = extractFrontmatter(data.content) as Manifest;
		if (compareVersion(manifest?.required_open_webui_version ?? '0.0.0', WEBUI_VERSION)) {
			console.log('Version is lower than required');
			toast.error(
				$i18n?.t?.(
					'Open WebUI version (v{{OPEN_WEBUI_VERSION}}) is lower than required version (v{{REQUIRED_VERSION}})',
					{
						OPEN_WEBUI_VERSION: WEBUI_VERSION,
						REQUIRED_VERSION: manifest?.required_open_webui_version ?? '0.0.0'
					}
				) ?? 'Version mismatch error'
			);
			return;
		}

		const res = await createNewTool(localStorage.token, {
			id: data.id,
			name: data.name,
			meta: data.meta,
			content: data.content,
			access_control: data.access_control
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n?.t?.('Tool created successfully') ?? 'Tool created successfully');
			tools.set(await getTools(localStorage.token));

			await goto('/workspace/tools');
		}
	};

	onMount(() => {
		window.addEventListener('message', async (event: MessageEvent) => {
			if (
				!['https://openwebui.com', 'https://www.openwebui.com', 'http://localhost:9999'].includes(
					event.origin
				)
			)
				return;

			try {
				tool = JSON.parse(event.data) as Tool;
				console.log(tool);
			} catch (error) {
				console.error('Failed to parse tool data:', error);
			}
		});

		if (window.opener ?? false) {
			window.opener.postMessage('loaded', '*');
		}

		if (sessionStorage.tool) {
			try {
				tool = JSON.parse(sessionStorage.tool) as Tool;
				sessionStorage.removeItem('tool');
				console.log(tool);
				clone = true;
			} catch (error) {
				console.error('Failed to parse tool from sessionStorage:', error);
			}
		}

		mounted = true;
	});
</script>

{#if mounted}
	{#key tool?.content}
		<ToolkitEditor
			id={tool?.id ?? ''}
			name={tool?.name ?? ''}
			meta={tool?.meta ?? { description: '' }}
			content={tool?.content ?? ''}
			accessControl={null}
			{clone}
			onSave={(value) => {
				saveHandler(value);
			}}
		/>
	{/key}
{/if}
