<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import { showSettings, mobile, showSidebar, config, user } from '$lib/stores';
	import { page } from '$app/state'
	import { fade } from 'svelte/transition';
	import { showKnowlegeManager } from '$lib/IONOS/stores/dialogs';
	import { signout } from '$lib/services/auths';
	import { buildSurveyUrl } from '$lib/IONOS/services/survey';
	import StacksIcon from '$lib/IONOS/components/icons/Stacks.svelte';
	import Gear from '$lib/IONOS/components/icons/Gear.svelte';
	import Logout from '$lib/IONOS/components/icons/Logout.svelte';
	import LightbulbShining from '$lib/IONOS/components/icons/LightbulbShining.svelte';
	import LifeRing from '$lib/IONOS/components/icons/LifeRing.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let className = 'max-w-[240px]';

	const dispatch = createEventDispatcher();

	const surveyUrl = buildSurveyUrl($user!);
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={(state) => {
		dispatch('change', state);
	}}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<slot name="content">
		<DropdownMenu.Content
			class="w-full {className} text-xs font-semibold rounded-2xl p-2.5 pr-3.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg font-primary flex flex-col gap-2"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			{#if page.url.pathname !== '/explore'}
				<button
					class="flex rounded-md p-2.5 w-full text-blue-800 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={async () => {
						await showSettings.set(true);
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<Gear />
					</div>
					<div class=" self-center truncate">{$i18n.t('Settings')}</div>
				</button>
			{/if}

			{#if page.url.pathname !== '/explore'}
				<button
					class="flex rounded-md p-2.5 w-full text-blue-800 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						showKnowlegeManager(true);
					}}
				>
					<div class=" self-center mr-3">
						<StacksIcon />
					</div>
					<div class=" self-center truncate">{$i18n.t('Knowledge')}</div>
				</button>
			{/if}

			{#if role === 'admin'}
				<a
					class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
					href="/playground"
					on:click={() => {
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M14.25 9.75 16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z"
							/>
						</svg>
					</div>
					<div class=" self-center truncate">{$i18n.t('Playground')}</div>
				</a>

				<a
					class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
					href="/admin"
					on:click={() => {
						show = false;

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z"
							/>
						</svg>
					</div>
					<div class=" self-center truncate">{$i18n.t('Admin Panel')}</div>
				</a>
			{/if}

			<a
				class="flex rounded-md p-2.5 w-full text-blue-800 hover:bg-gray-200 dark:hover:bg-gray-800 transition hidden" href="https://www.ionos.de/hilfe/"
				>
				<div class=" self-center mr-3">
					<LifeRing />
				</div>
				<div class=" self-center truncate">{$i18n.t('Help & FAQ', { ns: 'ionos' })}</div>
			</a>

			{#if surveyUrl}
				<button
					class="flex rounded-md p-2.5 w-full text-blue-800 hover:bg-gray-200 dark:hover:bg-gray-800 transition" on:click={() => {window.open(surveyUrl, '_blank', "noopener=yes,noreferrer=yes");}}>
					<div class=" self-center mr-3">
						<LightbulbShining />
					</div>
					<div class=" self-center truncate">{$i18n.t('Feedback', { ns: 'ionos' })}</div>
				</button>
			{/if}

			<button
				class="flex rounded-md p-2.5 w-full text-blue-800 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => { signout(); show = false; }}
			>
				<div class=" self-center mr-3">
					<Logout />
				</div>
				<div class=" self-center truncate">{$i18n.t('Sign Out')}</div>
			</button>

			<!-- <DropdownMenu.Item class="flex items-center px-3 py-2 text-sm ">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item> -->
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
