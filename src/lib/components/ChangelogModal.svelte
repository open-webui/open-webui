<script lang="ts">
	import DOMPurify from 'dompurify';

	import { onMount, getContext } from 'svelte';
	import { Confetti } from 'svelte-confetti';

	import { WEBUI_NAME, config, settings } from '$lib/stores';

	import { WEBUI_VERSION } from '$lib/constants';
	import { getChangelog } from '$lib/apis';

	import Modal from './common/Modal.svelte';
	import { updateUserSettings } from '$lib/apis/users';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	let changelog = null;

	const init = async () => {
		changelog = await getChangelog();
	};

	const closeModal = async () => {
		localStorage.version = $config.version;
		await settings.set({ ...$settings, ...{ version: $config.version } });
		await updateUserSettings(localStorage.token, { ui: $settings });
		show = false;
	};

	$: if (show) {
		init();
	}
</script>

<Modal bind:show size="xl">
	<div class="px-6 pt-5 dark:text-white text-black">
		<div class="flex justify-between items-start">
			<div class="text-xl font-medium">
				{$i18n.t("What's New in")}
				{$WEBUI_NAME}
				<Confetti x={[-1, -0.25]} y={[0, 0.5]} />
			</div>
			<button class="self-center" on:click={closeModal} aria-label={$i18n.t('Close')}>
				<XMark className={'size-5'}>
					<p class="sr-only">{$i18n.t('Close')}</p>
				</XMark>
			</button>
		</div>
		<div class="flex items-center mt-1">
			<div class="text-sm dark:text-gray-200">{$i18n.t('Release Notes')}</div>
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50/50 dark:bg-gray-850/50" />
			<div class="text-sm dark:text-gray-200">
				v{WEBUI_VERSION}
			</div>
		</div>
	</div>

	<div class=" w-full p-4 px-5 text-gray-700 dark:text-gray-100">
		<div class=" overflow-y-scroll max-h-[30rem] scrollbar-hidden">
			<div class="mb-3">
				{#if changelog}
					{#each Object.keys(changelog) as version}
						<div class=" mb-3 pr-2">
							<div class="font-semibold text-xl mb-1 dark:text-white">
								v{version} - {changelog[version].date}
							</div>

							<hr class="border-gray-50/50 dark:border-gray-850/50 my-2" />

							{#each Object.keys(changelog[version]).filter((section) => section !== 'date') as section}
								<div class="w-full">
									<div
										class="font-semibold uppercase text-xs {section === 'added'
											? 'bg-blue-500/20 text-blue-700 dark:text-blue-200'
											: section === 'fixed'
												? 'bg-green-500/20 text-green-700 dark:text-green-200'
												: section === 'changed'
													? 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200'
													: section === 'removed'
														? 'bg-red-500/20 text-red-700 dark:text-red-200'
														: ''}  w-fit rounded-xl px-2 my-2.5"
									>
										{section}
									</div>

									<div class="my-2.5 px-1.5 markdown-prose-sm !list-none !w-full !max-w-none">
										{#each changelog[version][section] as entry}
											<div class="my-2">
												{@html DOMPurify.sanitize(entry?.raw)}
											</div>
										{/each}
									</div>
								</div>
							{/each}
						</div>
					{/each}
				{/if}
			</div>
		</div>
		<div class="flex justify-end pt-3 text-sm font-medium">
			<button
				on:click={closeModal}
				class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			>
				<span class="relative">{$i18n.t("Okay, Let's Go!")}</span>
			</button>
		</div>
	</div>
</Modal>
