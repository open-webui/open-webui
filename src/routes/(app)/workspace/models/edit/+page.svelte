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

	const loadModel = async () => {
		const _id = $page.url.searchParams.get('id');
		if (_id) {
			const m = await getModelById(localStorage.token, _id).catch((e) => null);
			if (!m) {
				goto('/workspace/models');
				return;
			}
			if (!m?.write_access) {
				toast.error($i18n.t('You do not have permission to edit this model'));
				goto('/workspace/models');
				return;
			}
			return m;
		}
		goto('/workspace/models');
	};

	onMount(async () => {
		model = await loadModel();
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
	<ModelEditor
		edit={true}
		{model}
		{onSubmit}
		onReload={loadModel}
		onBack={async () => {
			await goto('/workspace/models');
		}}
	/>
{/if}
