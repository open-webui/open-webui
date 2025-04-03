<script lang="ts">
	import { marked } from 'marked';
	import markedExtension from '$lib/utils/marked/extension';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';
	import { onMount, getContext } from 'svelte';
	import Markdown from './chat/Messages/Markdown.svelte';

	import { settings } from '$lib/stores';

	import { getCustomModal } from '$lib/apis';

	import Modal from './common/Modal.svelte';
	import { updateUserSettings, getUserSettings } from '$lib/apis/users';

	const i18n = getContext('i18n');

	export let show = false;

	const options = {
		throwOnError: false
	};

	marked.use(markedKatexExtension(options));
	marked.use(markedExtension(options));

	let custom_modal = null;

	onMount(async () => {
		const res = await getCustomModal();
		custom_modal = res;
	});
</script>

<Modal bind:show size="lg">
	{#if show}
		<div class="px-5 pt-4 dark:text-gray-300 text-gray-700">
			<div class="flex justify-between items-start">
				<div class="text-xl font-semibold">
					<Markdown id="custom_login_modal_title" content={$i18n.t(custom_modal.title)} />
				</div>
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
			<!-- <div class="flex items-center mt-1">
				<div class="text-sm dark:text-gray-200">{$i18n.t('Release Notes')}</div>
				<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-200 dark:bg-gray-700" />
				<div class="text-sm dark:text-gray-200">
					v{WEBUI_VERSION}
				</div>
			</div> -->
		</div>

		<div class=" w-full p-4 px-5 text-gray-700 dark:text-gray-100">
			<div class=" overflow-y-scroll max-h-96 scrollbar-hidden">
				<div class="mb-3">
					
					<Markdown id="custom_login_modal_content" content={custom_modal.content} />
					
				</div>
			</div>
			<div class="flex justify-end pt-3 text-sm font-medium">
				<button
					on:click={async () => {
						await settings.set({ ...$settings, ...{ custom_login_modal_acknowledged: true } });
						await updateUserSettings(localStorage.token, { ui: $settings });
						show = false;
					}}
					class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
				>
					<span class="relative">{$i18n.t('Accept')}</span>
				</button>
			</div>
		</div>
	{/if}
</Modal>
