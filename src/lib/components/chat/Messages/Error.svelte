<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Modal from '$lib/components/common/Modal.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let content = '';

	let showDetailModal = false;

	// Extract a short message for display
	const getShortMessage = (content: any): string => {
		if (typeof content === 'string') {
			return content.length > 60 ? content.slice(0, 60) + '...' : content;
		} else if (typeof content === 'object' && content !== null) {
			if (content?.error?.message) {
				const msg = content.error.message;
				return msg.length > 60 ? msg.slice(0, 60) + '...' : msg;
			} else if (content?.detail) {
				const msg = content.detail;
				return typeof msg === 'string' && msg.length > 60 ? msg.slice(0, 60) + '...' : msg;
			} else if (content?.message) {
				const msg = content.message;
				return msg.length > 60 ? msg.slice(0, 60) + '...' : msg;
			}
		}
		return $i18n.t('An error occurred. Click for details.');
	};

	// Get full error content for modal
	const getFullContent = (content: any): string => {
		if (typeof content === 'string') {
			return content;
		} else if (typeof content === 'object' && content !== null) {
			return JSON.stringify(content, null, 2);
		}
		return String(content);
	};
</script>

<!-- Error Detail Modal -->
<Modal bind:show={showDetailModal} size="sm">
	<div class="p-6">
		<div class="flex items-center gap-3 mb-4">
			<div class="flex items-center justify-center w-8 h-8 rounded-full bg-[#FF4D6A]/10">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="#FF4D6A"
					class="w-5 h-5"
				>
					<path
						fill-rule="evenodd"
						d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<h3 class="text-title-4 text-gray-900 dark:text-gray-100">
				{$i18n.t('Error Details')}
			</h3>
		</div>

		<div
			class="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 max-h-[24rem] overflow-auto font-mono text-body-4 text-gray-700 dark:text-gray-300 whitespace-pre-wrap wrap-break-word"
		>
			{getFullContent(content)}
		</div>

		<div class="flex justify-end mt-4">
			<button
				type="button"
				class="px-4 py-2 text-body-4-medium text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition"
				on:click={() => (showDetailModal = false)}
			>
				{$i18n.t('Close')}
			</button>
		</div>
	</div>
</Modal>

<!-- Error Callout -->
<div
	class="flex flex-col justify-center items-start
		py-5 px-7 gap-4 my-2
		max-w-[30.625rem] w-fit
		bg-white/50 dark:bg-white/5
		border border-[#FF4D6A]
		shadow-[0.25rem_0.25rem_1.25rem_rgba(0,0,0,0.1),inset_0.125rem_0.125rem_0.625rem_rgba(255,255,255,0.05),inset_0.125rem_0.125rem_1rem_rgba(206,212,229,0.12)]
		backdrop-blur-[0.625rem]
		rounded-[1.25rem] rounded-bl-[0.25rem]"
>
	<div class="flex flex-row items-center gap-3">
		<!-- Error Icon Button -->
		<button
			type="button"
			class="shrink-0 w-5 h-5 cursor-pointer hover:opacity-80 transition"
			on:click={() => (showDetailModal = true)}
			aria-label={$i18n.t('Show error details')}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
				fill="#FF4D6A"
				class="w-5 h-5"
			>
				<path
					fill-rule="evenodd"
					d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z"
					clip-rule="evenodd"
				/>
			</svg>
		</button>

		<!-- Error Message -->
		<span class="text-body-4 text-gray-950 dark:text-gray-100">
			{getShortMessage(content)}
		</span>
	</div>
</div>
