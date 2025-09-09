<script lang="ts">
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
	let collapsedVersions = new Map();

	onMount(async () => {
		const res = await getChangelog();
		changelog = res;
	});
</script>

<Modal bind:show size="lg">
	<div class="px-5 pt-4 dark:text-gray-300 text-gray-700">
		<div class="flex justify-between items-start">
			<div class="text-xl font-semibold">
				{$i18n.t("What's New in")}
				{$WEBUI_NAME}
				<Confetti x={[-1, -0.25]} y={[0, 0.5]} />
			</div>
			<button
				class="self-center"
				on:click={() => {
					localStorage.version = $config.version;
					show = false;
				}}
				aria-label={$i18n.t('Close')}
			>
				<XMark className={'size-5'}>
					<p class="sr-only">{$i18n.t('Close')}</p>
				</XMark>
			</button>
		</div>
		<div class="flex items-center mt-1">
			<div class="text-sm dark:text-gray-200">{$i18n.t('Release Notes')}</div>
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-200 dark:bg-gray-700" />
			<div class="text-sm dark:text-gray-200">
				v{WEBUI_VERSION}
			</div>
		</div>
	</div>

	<div class=" w-full p-4 px-5 text-gray-700 dark:text-gray-100">
		<div class=" overflow-y-scroll max-h-96 scrollbar-hidden">
			<div class="mb-3">
				{#if changelog}
				    {#each Object.keys(changelog) as version, i}
				        {@const isCollapsed = collapsedVersions.get(version) ?? (i > 0)}

				        <div class="mb-3 pr-2">
				            <!-- 1. Make the header a button to toggle the collapsed state -->
				            <button
				                class="w-full flex justify-between items-center text-left"
				                on:click={() => collapsedVersions.set(version, !isCollapsed)}
				            >
				                <div class="font-semibold text-xl dark:text-white">
				                    v{version} - {changelog[version].date}
				                </div>

				                <svg
				                    class="size-4 transform transition-transform {isCollapsed ? '-rotate-90' : 'rotate-0'}"
				                    xmlns="http://www.w3.org/2000/svg"
				                    viewBox="0 0 20 20"
				                    fill="currentColor"
				                >
				                    <path
				                        fill-rule="evenodd"
				                        d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
				                        clip-rule="evenodd"
				                    />
				                </svg>
				            </button>

				            <hr class="border-gray-100 dark:border-gray-850 my-2" />

				            {#if !isCollapsed}
				                {#each Object.keys(changelog[version]).filter((section) => section !== 'date') as section}
				                    <div class="">
				                        <div
				                            class="font-semibold uppercase text-xs {section === 'added'
				                                ? 'text-white bg-blue-600'
				                                : section === 'fixed'
				                                    ? 'text-white bg-green-600'
				                                    : section === 'changed'
				                                        ? 'text-white bg-yellow-600'
				                                        : section === 'removed'
				                                            ? 'text-white bg-red-600'
				                                            : ''}  w-fit px-3 rounded-full my-2.5"
				                        >
				                            {section}
				                        </div>

				                        <ul class="my-2.5 px-1.5 space-y-2 changelog-content">
				                            {#each changelog[version][section] as entry}
				                                {@html `<div class="text-sm">${entry.raw}</div>`}
				                            {/each}
				                        </ul>
				                    </div>
				                {/each}
				            {/if}
				        </div>
				    {/each}
				{/if}
			</div>
		</div>
		<div class="flex justify-end pt-3 text-sm font-medium">
			<button
				on:click={async () => {
					localStorage.version = $config.version;
					await settings.set({ ...$settings, ...{ version: $config.version } });
					await updateUserSettings(localStorage.token, { ui: $settings });
					show = false;
				}}
				class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			>
				<span class="relative">{$i18n.t("Okay, Let's Go!")}</span>
			</button>
		</div>
	</div>
</Modal>

<style>
    :global(.changelog-content li) {
        list-style-type: none;
        padding-left: 0;
    }

    :global(.changelog-content p) {
        margin: 0;
    }

    :global(.changelog-content a) {
        text-decoration-line: underline !important;
        color: theme('colors.blue.600') !important;
    }

    :global(.dark .changelog-content a) {
        color: theme('colors.blue.400') !important;
    }
</style>
