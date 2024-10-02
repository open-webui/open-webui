<script lang="ts">
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getKnowledgeById } from '$lib/apis/knowledge';
	import Spinner from '$lib/components/common/Spinner.svelte';

	let id = null;
	let knowledge = null;

	onMount(async () => {
		id = $page.params.id;

		const res = await getKnowledgeById(localStorage.token, id).catch((e) => {
			console.error(e);
		});

		if (res) {
			knowledge = res;
		} else {
			goto('/workspace/knowledge');
		}
	});
</script>

<div class="w-full max-h-full">
	<button
		class="flex space-x-1"
		on:click={() => {
			goto('/workspace/knowledge');
		}}
	>
		<div class=" self-center">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					fill-rule="evenodd"
					d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
		<div class=" self-center font-medium text-sm">{$i18n.t('Back')}</div>
	</button>

	<div class="flex flex-col my-2">
		{#if id && knowledge}
			<div>
				<div>
					<div class=" font-medium text-xl font-primary">
						{knowledge.name}
					</div>
					<div class=" line-clamp-2 font-medium text-sm">
						{knowledge.description}
					</div>
				</div>
			</div>
		{:else}
			<Spinner />
		{/if}
	</div>
</div>
