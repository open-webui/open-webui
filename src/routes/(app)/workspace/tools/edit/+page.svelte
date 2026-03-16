<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getToolById, getTools, updateToolById } from '$lib/apis/tools';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ToolkitEditor from '$lib/components/workspace/Tools/ToolkitEditor.svelte';
	import { WEBUI_VERSION } from '$lib/constants';
	import { tools } from '$lib/stores';
	import { compareVersion, extractFrontmatter } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let tool = null;

	const saveHandler = async (data) => {
		console.log(data);

		const manifest = extractFrontmatter(data.content);
		if (compareVersion(manifest?.required_open_webui_version ?? '0.0.0', WEBUI_VERSION)) {
			console.log('Version is lower than required');
			toast.error(
				$i18n.t(
					'Open WebUI version (v{{OPEN_WEBUI_VERSION}}) is lower than required version (v{{REQUIRED_VERSION}})',
					{
						OPEN_WEBUI_VERSION: WEBUI_VERSION,
						REQUIRED_VERSION: manifest?.required_open_webui_version ?? '0.0.0'
					}
				)
			);
			return;
		}

		const res = await updateToolById(localStorage.token, tool.id, {
			id: data.id,
			name: data.name,
			meta: data.meta,
			content: data.content,
			access_grants: data.access_grants
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Tool updated successfully'));
			tools.set(await getTools(localStorage.token));

			// await goto('/workspace/tools');
		}
	};

	onMount(async () => {
		console.log('mounted');
		const id = $page.url.searchParams.get('id');

		if (id) {
			const res = await getToolById(localStorage.token, id).catch((error) => {
				toast.error(`${error}`);
				goto('/workspace/tools');
				return null;
			});

			if (res && !res.write_access) {
				toast.error($i18n.t('You do not have permission to edit this tool'));
				goto('/workspace/tools');
				return;
			}

			if (res) {
				tool = res;
				console.log(tool);
			}
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
		accessGrants={tool.access_grants ?? []}
		onSave={(value) => {
			saveHandler(value);
		}}
	/>
{:else}
	<div class="flex items-center justify-center h-full">
		<div class=" pb-16">
			<Spinner className="size-5" />
		</div>
	</div>
{/if}
