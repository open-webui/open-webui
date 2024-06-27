<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { functions, models } from '$lib/stores';
	import { createNewFunction, getFunctions } from '$lib/apis/functions';
	import FunctionEditor from '$lib/components/workspace/Functions/FunctionEditor.svelte';
	import { getModels } from '$lib/apis';

	const i18n = getContext('i18n');

	let mounted = false;
	let clone = false;
	let func = null;

	const saveHandler = async (data) => {
		console.log(data);
		const res = await createNewFunction(localStorage.token, {
			id: data.id,
			name: data.name,
			meta: data.meta,
			content: data.content
		}).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Function created successfully'));
			functions.set(await getFunctions(localStorage.token));
			models.set(await getModels(localStorage.token));

			await goto('/workspace/functions');
		}
	};

	onMount(() => {
		window.addEventListener('message', async (event) => {
			if (
				!['https://openwebui.com', 'https://www.openwebui.com', 'http://localhost:9999'].includes(
					event.origin
				)
			)
				return;

			func = JSON.parse(event.data);
			console.log(func);
		});

		if (window.opener ?? false) {
			window.opener.postMessage('loaded', '*');
		}

		if (sessionStorage.function) {
			func = JSON.parse(sessionStorage.function);
			sessionStorage.removeItem('function');

			console.log(func);
			clone = true;
		}

		mounted = true;
	});
</script>

{#if mounted}
	{#key func?.content}
		<FunctionEditor
			id={func?.id ?? ''}
			name={func?.name ?? ''}
			meta={func?.meta ?? { description: '' }}
			content={func?.content ?? ''}
			{clone}
			on:save={(e) => {
				saveHandler(e.detail);
			}}
		/>
	{/key}
{/if}
