<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '../common/Modal.svelte';

	export let show = false;
	export let onConfirm = () => {};
	export let onCancel = () => {};

	const i18n = getContext('i18n');
</script>

<Modal bind:show size="md">
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-0.5">
			<div class="text-lg font-medium self-center">{$i18n.t('Web Search Privacy Notice')}</div>
			<button
				class="self-center"
				on:click={() => {
					onCancel();
					show = false;
				}}
			>
			</button>
		</div>

		<div class="px-5 pt-4 pb-5 w-full flex flex-col justify-center">
			<div class="text-sm dark:text-gray-300 mb-4">
				{$i18n.t("When you use web search, your entire prompt or parts of it — including any confidential information or personal data — will be sent to the open internet. Please review your prompt and ensure it complies with your company's data security guidelines.")}
			</div>

			<div class="flex justify-end">
				<div class="flex gap-2">
					<button
						class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-800 transition rounded-full"
						type="button"
						on:click={() => {
							onCancel();
							show = false;
						}}
					>
						{$i18n.t('Cancel')}
					</button>

					<button
						class="self-center flex items-center gap-1 px-3.5 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						type="button"
						on:click={() => {
							onConfirm();
							show = false;
						}}
					>
						{$i18n.t('Enable')}
					</button>
				</div>
			</div>
		</div>
	</div>
</Modal>