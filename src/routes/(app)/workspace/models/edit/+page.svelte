<script>
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { page } from '$app/stores';
	import { config, models, settings } from '$lib/stores';

	import { getModelById, updateModelById } from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import ModelEditor from '$lib/components/workspace/Models/ModelEditor.svelte';

	let model = null;
	let write_access = true;

	onMount(async () => {
		const _id = $page.url.searchParams.get('id');
		if (_id) {
			
			// Get model list to check write_access
			const modelList = await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			).catch(() => []);
			
			// If getModels returns an object with items (ModelAccessListResponse), use items
			// Otherwise assume it's a list (old behavior or if API returns list)
			const items = Array.isArray(modelList) ? modelList : modelList.items;
			
			const modelWithAccess = items.find(m => m.id === _id);
			write_access = modelWithAccess?.write_access ?? true;

			model = await getModelById(localStorage.token, _id).catch((e) => {
				return null;
			});

			if (!model) {
				goto('/workspace/models');
			}
		} else {
			goto('/workspace/models');
		}
	});

	const onSubmit = async (modelInfo) => {
		const res = await updateModelById(localStorage.token, modelInfo.id, modelInfo);

		if (res) {
			await models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
			toast.success($i18n.t('Model updated successfully'));
			await goto('/workspace/models');
		}
	};
</script>

{#if model}
	<ModelEditor edit={true} {model} {write_access} {onSubmit} />
{/if}
