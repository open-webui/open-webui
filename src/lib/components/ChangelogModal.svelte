<script lang="ts">
	import DOMPurify from 'dompurify';

	import { getContext } from 'svelte';

	import { WEBUI_NAME, config, settings } from '$lib/stores';

	import { WEBUI_VERSION } from '$lib/constants';
	import { getChangelog } from '$lib/apis';

	import Modal from './common/Modal.svelte';
	import { updateUserSettings } from '$lib/apis/users';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	type ChangelogEntry = {
		raw?: string;
	};
	type ChangelogVersion = {
		date: string;
		[section: string]: string | ChangelogEntry[];
	};

	let changelog: Record<string, ChangelogVersion> | null = null;
	let error = false;

	const init = async () => {
		if (changelog || error) {
			return;
		}

		changelog = await getChangelog().catch(() => {
			error = true;
			return null;
		});
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

	const formatDate = (date: string) => {
		if (!date) {
			return '';
		}

		const [year, month, day] = date.split('-');
		const months = [
			'Jan',
			'Feb',
			'Mar',
			'Apr',
			'May',
			'Jun',
			'Jul',
			'Aug',
			'Sep',
			'Oct',
			'Nov',
			'Dec'
		];
		const monthIndex = Number(month) - 1;

		return year && monthIndex >= 0 && monthIndex < months.length && day
			? `${months[monthIndex]} ${Number(day)}, ${year}`
			: date;
	};

	const getSectionEntries = (version: string, section: string) => {
		const entries = changelog?.[version]?.[section];
		return Array.isArray(entries) ? entries : [];
	};
</script>

<Modal
	bind:show
	size="lg"
	className="bg-white dark:bg-gray-900 rounded-3xl overflow-hidden"
	containerClassName="p-3"
>
	<div class="flex max-h-[58vh] flex-col">
		<div
			class="flex shrink-0 items-start justify-between gap-4 px-4 pb-2.5 pt-3.5 dark:text-white text-black"
		>
			<div class="min-w-0">
				<h2 class="m-0 truncate text-base font-normal">
					{$i18n.t("What's New in")}
					{$WEBUI_NAME}
				</h2>
				<div class="mt-1 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
					<span>{$i18n.t('Release Notes')}</span>
					<span class="h-1 w-1 rounded-full bg-gray-300 dark:bg-gray-700"></span>
					<span>v{WEBUI_VERSION}</span>
				</div>
			</div>

			<button
				class="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-gray-400 transition hover:bg-gray-100 hover:text-gray-700 dark:text-gray-500 dark:hover:bg-white/10 dark:hover:text-gray-200"
				on:click={closeModal}
				aria-label={$i18n.t('Close')}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div
			class="min-h-0 flex-1 overflow-y-auto px-4 py-2 text-gray-700 scrollbar-hidden dark:text-gray-100"
		>
			{#if changelog}
				<div class="space-y-4">
					{#each Object.keys(changelog) as version}
						<section class="pr-1">
							<div class="mb-2">
								<h3 class="m-0 text-sm font-normal text-gray-950 dark:text-white">v{version}</h3>
								<div class="mt-0.5 text-[0.6875rem] text-gray-400 dark:text-gray-500">
									{formatDate(changelog[version].date)}
								</div>
							</div>

							{#each Object.keys(changelog[version]).filter((section) => section !== 'date') as section}
								<div class="mb-3 w-full">
									<div
										class="mb-2 text-[0.6875rem] font-normal uppercase tracking-wide {section ===
										'added'
											? 'text-blue-600 dark:text-blue-300'
											: section === 'fixed'
												? 'text-green-600 dark:text-green-300'
												: section === 'changed'
													? 'text-yellow-700 dark:text-yellow-300'
													: section === 'removed'
														? 'text-red-600 dark:text-red-300'
														: 'text-gray-500 dark:text-gray-400'}"
									>
										{section}
									</div>

									<div class="space-y-2 text-[0.8125rem] leading-relaxed">
										{#each getSectionEntries(version, section) as entry}
											<div class="flex gap-2.5">
												<span
													class="mt-[0.6em] h-1 w-1 shrink-0 rounded-full bg-gray-300 dark:bg-gray-700"
												></span>
												<div
													class="min-w-0 markdown-prose-sm !max-w-none !text-[0.8125rem] text-gray-600 dark:text-gray-300 [&_*]:!my-0 [&_b]:!font-normal [&_strong]:!font-normal"
												>
													<!-- eslint-disable-next-line svelte/no-at-html-tags -->
													{@html DOMPurify.sanitize(entry?.raw)}
												</div>
											</div>
										{/each}
									</div>
								</div>
							{/each}
						</section>
					{/each}
				</div>
			{:else if error}
				<div class="flex flex-col items-center justify-center gap-3 py-16 text-center">
					<p class="text-sm text-gray-500 dark:text-gray-400">
						{$i18n.t('Could not load release notes.')}
					</p>
					<button
						on:click={() => {
							error = false;
							init();
						}}
						class="text-sm font-normal text-gray-700 transition hover:text-black dark:text-gray-300 dark:hover:text-white"
					>
						{$i18n.t('Retry')}
					</button>
				</div>
			{:else}
				<div
					class="flex items-center justify-center py-16 text-sm text-gray-400 dark:text-gray-500"
				>
					{$i18n.t('Loading release notes...')}
				</div>
			{/if}
		</div>

		<div class="flex shrink-0 justify-end px-4 pb-3.5 pt-1.5 text-sm">
			<button
				on:click={closeModal}
				class="font-normal text-gray-600 transition hover:text-gray-950 dark:text-gray-400 dark:hover:text-white"
			>
				<span class="relative">{$i18n.t("Okay, Let's Go!")}</span>
			</button>
		</div>
	</div>
</Modal>
