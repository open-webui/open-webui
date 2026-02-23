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

	onMount(async () => {
		const _id = $page.url.searchParams.get('id');
		if (_id) {
			model = await getModelById(localStorage.token, _id).catch(() => {
				return null;
			});

			if (!model) {
				goto('/workspace/agents');
			}

			if (model?.kind !== 'agent') {
				goto('/workspace/agents');
			}

			if (!model?.write_access) {
				toast.error($i18n.t('You do not have permission to edit this model'));
				goto('/workspace/agents');
			}
		} else {
			goto('/workspace/agents');
		}
	});

	const onSubmit = async (modelInfo) => {
		const res = await updateModelById(localStorage.token, modelInfo.id, {
			...modelInfo,
			kind: 'agent'
		});

		if (res) {
			await models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
			toast.success($i18n.t('Agent updated successfully'));
			await goto('/workspace/agents');
		}
	};
</script>

{#if model}
	<ModelEditor edit={true} {model} {onSubmit} />
{/if}
