<script lang="ts">
	import { getContext } from 'svelte';
	import Selector from './Knowledge/Selector.svelte';

	export let knowledge = [];

	const i18n = getContext('i18n');
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-sm font-semibold">{$i18n.t('Knowledge')}</div>
	</div>

	<div class=" text-xs dark:text-gray-500">
		{$i18n.t('To add documents here, upload them to the "Documents" workspace first.')}
	</div>

	<div class="flex flex-col">
		{#if knowledge.length > 0}
			<div class=" flex items-center gap-2 mt-2">
				{#each knowledge as file, fileIdx}
					<div class=" relative group">
						<div
							class="h-16 w-[15rem] flex items-center space-x-3 px-2.5 dark:bg-gray-600 rounded-xl border border-gray-200 dark:border-none"
						>
							<div class="p-2.5 bg-red-400 text-white rounded-lg">
								{#if (file?.type ?? 'doc') === 'doc'}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="size-6"
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
								{:else if file.type === 'collection'}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="size-6"
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

							<div class="flex flex-col justify-center -space-y-0.5">
								<div class=" dark:text-gray-100 text-sm font-medium line-clamp-1">
									{file?.title ?? `#${file.name}`}
								</div>

								<div class=" text-gray-500 text-sm">{$i18n.t(file?.type ?? 'Document')}</div>
							</div>
						</div>

						<div class=" absolute -top-1 -right-1">
							<button
								class=" bg-gray-400 text-white border border-white rounded-full group-hover:visible invisible transition"
								type="button"
								on:click={() => {
									knowledge.splice(fileIdx, 1);
									knowledge = knowledge;
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
									/>
								</svg>
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<div class="flex flex-wrap text-sm font-medium gap-1.5 mt-2">
			<Selector bind:knowledge>
				<button
					class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-300 dark:outline-gray-800 rounded-3xl"
					type="button">{$i18n.t('Select Documents')}</button
				>
			</Selector>
		</div>
		<!-- {knowledge} -->
	</div>
</div>
