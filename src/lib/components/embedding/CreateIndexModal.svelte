<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '../common/Modal.svelte';
	import {createNewIndex} from "$lib/apis/embedding/index.js";

	const i18n = getContext('i18n');

	export let show = false;
	export let onClose: Function

	let name = ''
	let category = ''
	let geographic = ''

	const handleCreateIndex = async () => {
		const embeddingIndex = await createNewIndex(name, category, geographic)
		onClose?.(embeddingIndex)
	}
</script>

<Modal bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4">
			<div class=" text-lg font-medium self-center">{$i18n.t('Create new embedding index')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full p-8 md:space-x-4">
			<div class="flex-1 md:min-h-[300px]">
				<div class=" mb-2 text-sm font-medium">{$i18n.t('Embedding Model')}</div>
				<div class="flex-1 mr-2">
					<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t("Index name")}
							bind:value={name}
					/>
				</div>

				<div class="mt-4 mb-2 text-sm font-medium">{$i18n.t('Category')}</div>
				<div class="flex-1 mr-2">
					<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t("Category")}
							bind:value={category}
					/>
				</div>

				<div class="mt-4 mb-2 text-sm font-medium">{$i18n.t('Geographic')}</div>
				<div class="flex-1 mr-2">
					<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t("Geographic")}
							bind:value={geographic}
					/>
				</div>

				<div class="flex justify-end pt-5 mr-2 text-sm font-medium">
					<button
							class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
							type="submit"
							on:click={() => handleCreateIndex()}
					>
						{$i18n.t('Create')}
					</button>
				</div>
			</div>
		</div>
	</div>
</Modal>
