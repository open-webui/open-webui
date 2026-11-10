<script>
	import { getPageContext } from '$lib/utils/page';
	const { goto, url: pageUrl } = getPageContext();

	import { toast } from 'svelte-sonner';

	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { config, models, settings } from '$lib/stores';

	import { getModelById, updateModelById } from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import ModelEditor from '$lib/components/workspace/Models/ModelEditor.svelte';

	let model = null;

	onMount(async () => {
		const _id = $pageUrl.searchParams.get('id');
		if (_id) {
			model = await getModelById(localStorage.token, _id).catch((e) => {
				return null;
			});

			if (!model) {
				goto('/workspace/models');
				return;
			}

			if (!model?.write_access) {
				toast.error($i18n.t('You do not have permission to edit this model'));
				goto('/workspace/models');
			}
		} else {
			goto('/workspace/models');
		}
	});

	const onSubmit = async (modelInfo) => {
		const res = await updateModelById(localStorage.token, modelInfo.id, modelInfo);

		if (res) {
			try {
				await models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections
							? ($settings?.directConnections ?? null)
							: null
					)
				);
				toast.success($i18n.t('Model updated successfully'));
				await goto('/workspace/models');
			} catch (error) {
				toast.error(`${error}`);
			}
			return res;
		}
		return false;
	};
	import PageTitle from '$lib/components/common/PageTitle.svelte';
	import { WEBUI_NAME } from '$lib/stores';
</script>

<PageTitle title={(model?.name || $i18n.t('Edit Model')) + ' / ' + $WEBUI_NAME} />

{#if model}
	<ModelEditor
		edit={true}
		{model}
		{onSubmit}
		onBack={async () => {
			await goto('/workspace/models');
		}}
	/>
{/if}
