<script>
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { config, models, settings } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import { onMount, getContext } from 'svelte';
	import { createNewModel } from '$lib/apis/models';
	import { getModels } from '$lib/apis';

	import ModelEditor from '$lib/components/workspace/Models/ModelEditor.svelte';

	const i18n = getContext('i18n');

	const onSubmit = async (modelInfo) => {
		if ($models.find((m) => m.id === modelInfo.id)) {
			toast.error(
				$i18n.t(
					"Error: A model with the ID '{{modelId}}' already exists. Please select a different ID to proceed.",
					{ modelId: modelInfo.id }
				)
			);
			return;
		}

		if (modelInfo.id === '') {
			toast.error($i18n.t('Error: Model ID cannot be empty. Please enter a valid ID to proceed.'));
			return;
		}

		const res = await createNewModel(localStorage.token, {
			...modelInfo,
			kind: 'agent',
			meta: {
				...modelInfo.meta,
				profile_image_url: modelInfo.meta.profile_image_url ?? `${WEBUI_BASE_URL}/static/favicon.png`,
				suggestion_prompts: modelInfo.meta.suggestion_prompts
					? modelInfo.meta.suggestion_prompts.filter((prompt) => prompt.content !== '')
					: null
			},
			params: { ...modelInfo.params }
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			await models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
			toast.success($i18n.t('Agent created successfully!'));
			await goto('/workspace/agents');
		}
	};

	let model = null;

	onMount(async () => {
		if (sessionStorage.model) {
			model = JSON.parse(sessionStorage.model);
			sessionStorage.removeItem('model');
		}
	});
</script>

{#key model}
	<ModelEditor {model} {onSubmit} />
{/key}
