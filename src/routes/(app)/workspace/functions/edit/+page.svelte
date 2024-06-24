<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { functions, models } from '$lib/stores';
	import { updateFunctionById, getFunctions, getFunctionById } from '$lib/apis/functions';

	import FunctionEditor from '$lib/components/workspace/Functions/FunctionEditor.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getModels } from '$lib/apis';

	const i18n = getContext('i18n');

	let func = null;

	const saveHandler = async (data) => {
		console.log(data);
		const res = await updateFunctionById(localStorage.token, func.id, {
			id: data.id,
			name: data.name,
			meta: data.meta,
			content: data.content
		}).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Function updated successfully'));
			functions.set(await getFunctions(localStorage.token));
			models.set(await getModels(localStorage.token));
		}
	};

	onMount(async () => {
		console.log('mounted');
		const id = $page.url.searchParams.get('id');

		if (id) {
			func = await getFunctionById(localStorage.token, id).catch((error) => {
				toast.error(error);
				goto('/workspace/functions');
				return null;
			});

			console.log(func);
		}
	});
</script>

{#if func}
	<FunctionEditor
		edit={true}
		id={func.id}
		name={func.name}
		meta={func.meta}
		content={func.content}
		on:save={(e) => {
			saveHandler(e.detail);
		}}
	/>
{:else}
	<div class="flex items-center justify-center h-full">
		<div class=" pb-16">
			<Spinner />
		</div>
	</div>
{/if}
