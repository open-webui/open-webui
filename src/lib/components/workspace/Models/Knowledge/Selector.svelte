<script lang="ts">
	import { DropdownMenu } from 'bits-ui';

	import { documents } from '$lib/stores';
	import { flyAndScale } from '$lib/utils/transitions';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let onClose: Function = () => {};

	export let knowledge = [];

	let items = [];

	onMount(() => {
		let collections = [
			...($documents.length > 0
				? [
						{
							name: 'All Documents',
							type: 'collection',
							title: $i18n.t('All Documents'),
							collection_names: $documents.map((doc) => doc.collection_name)
						}
				  ]
				: []),
			...$documents
				.reduce((a, e, i, arr) => {
					return [...new Set([...a, ...(e?.content?.tags ?? []).map((tag) => tag.name)])];
				}, [])
				.map((tag) => ({
					name: tag,
					type: 'collection',
					collection_names: $documents
						.filter((doc) => (doc?.content?.tags ?? []).map((tag) => tag.name).includes(tag))
						.map((doc) => doc.collection_name)
				}))
		];

		items = [...collections, ...$documents];
	});
</script>

<Dropdown
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[300px]  rounded-lg px-1 py-1.5 border border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<div class="max-h-[10rem] overflow-y-scroll">
				{#if items.length === 0}
					<div class="text-center text-sm text-gray-500 dark:text-gray-400">
						{$i18n.t('No documents found')}
					</div>
				{:else}
					{#each items as item}
						<DropdownMenu.Item
							class="flex gap-2.5 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
							on:click={() => {
								if (!knowledge.find((k) => k.name === item.name)) {
									knowledge = [
										...knowledge,
										{
											...item,
											type: item?.type ?? 'doc'
										}
									];
								}
							}}
						>
							<div class="flex self-start">
								{#if (item?.type ?? 'doc') === 'doc'}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="w-4"
									>
										<path
											fill-rule="evenodd"
											d="M5.625 1.5c-1.036 0-1.875.84-1.875 1.875v17.25c0 1.035.84 1.875 1.875 1.875h12.75c1.035 0 1.875-.84 1.875-1.875V12.75A3.75 3.75 0 0 0 16.5 9h-1.875a1.875 1.875 0 0 1-1.875-1.875V5.25A3.75 3.75 0 0 0 9 1.5H5.625ZM7.5 15a.75.75 0 0 1 .75-.75h7.5a.75.75 0 0 1 0 1.5h-7.5A.75.75 0 0 1 7.5 15Zm.75 2.25a.75.75 0 0 0 0 1.5H12a.75.75 0 0 0 0-1.5H8.25Z"
											clip-rule="evenodd"
										/>
										<path
											d="M12.971 1.816A5.23 5.23 0 0 1 14.25 5.25v1.875c0 .207.168.375.375.375H16.5a5.23 5.23 0 0 1 3.434 1.279 9.768 9.768 0 0 0-6.963-6.963Z"
										/>
									</svg>
								{:else if item.type === 'collection'}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="size-4"
									>
										<path
											d="M7.5 3.375c0-1.036.84-1.875 1.875-1.875h.375a3.75 3.75 0 0 1 3.75 3.75v1.875C13.5 8.161 14.34 9 15.375 9h1.875A3.75 3.75 0 0 1 21 12.75v3.375C21 17.16 20.16 18 19.125 18h-9.75A1.875 1.875 0 0 1 7.5 16.125V3.375Z"
										/>
										<path
											d="M15 5.25a5.23 5.23 0 0 0-1.279-3.434 9.768 9.768 0 0 1 6.963 6.963A5.23 5.23 0 0 0 17.25 7.5h-1.875A.375.375 0 0 1 15 7.125V5.25ZM4.875 6H6v10.125A3.375 3.375 0 0 0 9.375 19.5H16.5v1.125c0 1.035-.84 1.875-1.875 1.875h-9.75A1.875 1.875 0 0 1 3 20.625V7.875C3 6.839 3.84 6 4.875 6Z"
										/>
									</svg>
								{/if}
							</div>

							<div class="flex items-center">
								<div class="flex flex-col">
									<div
										class=" w-fit text-xs font-black px-1 rounded uppercase line-clamp-1 bg-gray-500/20 text-gray-700 dark:text-gray-200"
									>
										{item?.type ?? 'Document'}
									</div>

									<div class="line-clamp-1 font-medium pr-0.5">
										{item.name}
									</div>
								</div>
							</div>
						</DropdownMenu.Item>
					{/each}
				{/if}
			</div>
		</DropdownMenu.Content>
	</div>
</Dropdown>
