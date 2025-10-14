<script>
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { config, models, settings } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import { onMount, tick, getContext } from 'svelte';
	import { createNewModel, getModelById } from '$lib/apis/models';
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

		if (modelInfo) {
			const res = await createNewModel(localStorage.token, {
				...modelInfo,
				meta: {
					...modelInfo.meta,
					profile_image_url:
						modelInfo.meta.profile_image_url ?? `${WEBUI_BASE_URL}/static/favicon.png`,
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
				toast.success($i18n.t('Model created successfully!'));
				await goto('/workspace/models');
			}
		}
	};

	let model = null;

	onMount(async () => {
		window.addEventListener('message', async (event) => {
			if (
				!['https://openwebui.com', 'https://www.openwebui.com', 'http://localhost:5173'].includes(
					event.origin
				)
			) {
				return;
			}

			try {
				let data = JSON.parse(event.data);

				if (data?.info) {
					data = data.info;
				}

				model = data;
			} catch (e) {
				console.error('Failed to parse message data:', e);
			}
		});

		if (window.opener ?? false) {
			window.opener.postMessage('loaded', '*');
		}

		if (sessionStorage.model) {
			model = JSON.parse(sessionStorage.model);
			sessionStorage.removeItem('model');
		}
	});
</script>

{#key model}
	<ModelEditor {model} {onSubmit} />
{/key}
