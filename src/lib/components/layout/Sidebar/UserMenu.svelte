<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import { showSettings, activeUserCount, USAGE_POOL } from '$lib/stores';
	import { fade, slide } from 'svelte/transition';
	import { getBackendConfig } from '$lib/apis';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let className = 'max-w-[240px]';

	const dispatch = createEventDispatcher();
	let modelStatus = '';
	let lobeChat_url = '';

	const init = async () => {
		try {
			const backendConfig = await getBackendConfig(localStorage.token);
			if (backendConfig) {
				modelStatus = backendConfig.model_status;
				lobeChat_url = backendConfig.lobeChat_url;
			} else {
				console.log('backendConfig is null or undefined');
			}
		} catch (err) {
			console.error('Error fetching backendConfig:', err);
		}
	};
	init();
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
			class="w-full {className} text-sm rounded-xl px-1 py-1.5 border border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<button
				class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					await showSettings.set(true);
					show = false;
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
							d="M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93.398.164.855.142 1.205-.108l.737-.527a1.125 1.125 0 011.45.12l.773.774c.39.389.44 1.002.12 1.45l-.527.737c-.25.35-.272.806-.107 1.204.165.397.505.71.93.78l.893.15c.543.09.94.56.94 1.109v1.094c0 .55-.397 1.02-.94 1.11l-.893.149c-.425.07-.765.383-.93.78-.165.398-.143.854.107 1.204l.527.738c.32.447.269 1.06-.12 1.45l-.774.773a1.125 1.125 0 01-1.449.12l-.738-.527c-.35-.25-.806-.272-1.203-.107-.397.165-.71.505-.781.929l-.149.894c-.09.542-.56.94-1.11.94h-1.094c-.55 0-1.019-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93-.398-.164-.854-.142-1.204.108l-.738.527c-.447.32-1.06.269-1.45-.12l-.773-.774a1.125 1.125 0 01-.12-1.45l.527-.737c.25-.35.273-.806.108-1.204-.165-.397-.505-.71-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.765-.383.93-.78.165-.398.143-.854-.107-1.204l-.527-.738a1.125 1.125 0 01.12-1.45l.773-.773a1.125 1.125 0 011.45-.12l.737.527c.35.25.807.272 1.204.107.397-.165.71-.505.78-.929l.15-.894z"
						/>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
						/>
					</svg>
				</div>
				<div class=" self-center font-medium">{$i18n.t('Settings')}</div>
			</button>

			<button
				class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={() => {
					dispatch('show', 'archived-chat');
					show = false;
				}}
			>
				<div class=" self-center mr-3">
					<ArchiveBox className="size-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center font-medium">{$i18n.t('Archived Chats')}</div>
			</button>

			{#if modelStatus}
				<button
					class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={() => {
						window.open(modelStatus, '_blank');
						showDropdown = false;
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
								d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37zM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 013 13.179z"
							/>
						</svg>
					</div>
					<div class=" self-center font-medium">{$i18n.t('Model Status')}</div>
				</button>
			{/if}

			{#if lobeChat_url}
				<button
					class="flex rounded-md py-2.5 px-3.5 w-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={() => {
						window.open(lobeChat_url, '_blank');
						showDropdown = false;
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
							<title>LobeHub</title>
							<path
								d="M22.951 13.475C22.951 19.672 18.082 24 11.975 24 5.87 24 1 19.59 1 13.393c0-1.843.41-2.633 2.58-2.922 3.89-.518 5.942-.313 8.396-.313 2.453 0 5.942-.104 8.395.313 2.007.342 2.457.71 2.58 3.004z"
								fill="#BFBFBF"
							/>
							<path
								d="M11.955 19.209c-2.314 0-2.928.286-2.928.286s.287 2.212 2.928 2.212c2.642 0 2.928-2.212 2.928-2.212s-.614-.287-2.928-.287z"
								fill="#4F4F4F"
							/>
							<ellipse cx="12.017" cy="11.509" fill="#838383" rx="9.133" ry=".942" /><path
								d="M9.969 12.451c.052-1.226-.04-1.867-.45-2.985 0 0 .777-.987 2.21-.987 1.434 0 2.458.25 2.458.25-.248 1.376-.26 2.206-.205 3.722H9.97z"
								fill="#E1E1E1"
							/>
							<path
								d="M8.633 18.535c1.207-.58 2.032-1.762 2.032-3.217 0-2.081-1.687-3.932-3.768-3.932-2.08 0-3.85 1.605-3.85 3.686 0 1.146.537 2.196 1.365 2.91a4.582 4.582 0 011.625-.289c1.04 0 1.972.327 2.596.842zM15.318 18.535c-1.207-.58-2.032-1.762-2.032-3.217 0-2.081 1.687-3.932 3.768-3.932 2.08 0 3.85 1.605 3.85 3.686 0 1.146-.537 2.196-1.365 2.91a4.582 4.582 0 00-1.625-.289c-1.04 0-1.972.327-2.596.842z"
								fill="#fff"
							/>
							<path
								d="M16.808 17.447a2.293 2.293 0 110-4.586 2.293 2.293 0 010 4.586zM7.143 17.447a2.293 2.293 0 100-4.586 2.293 2.293 0 000 4.586z"
								fill="#1A1A1A"
							/>
							<path
								d="M13.04.902c-1.149 0-1.597-.942-3.358-.9-1.916 0-2.785 1.064-3.727 1.883-.16.14-.942.574-1.31.737-1.612.717-2.826 1.761-2.826 3.318 0 1.696 1.43 3.071 3.194 3.071.29 0 .57-.037.838-.106.712.863 1.816 1.364 3.053 1.417 1.925.082 2.54-1.25 3.645-.697.758.38 1.133.697 2.334.697 1.402 0 2.053-.43 2.457-.901.738-.86 1.874-.328 2.58-.328 1.538 0 2.785-1.192 2.785-2.662s-1.246-2.662-2.784-2.662c-.422 0-1.217.104-1.393-.573C18.241 2.09 16.878.82 14.924.82c-.763 0-1.449.082-1.884.082z"
								fill="#838383"
							/>
							<circle cx="4.891" cy="1.025" fill="#838383" r=".778" /><circle
								cx="20.699"
								cy="3.4"
								fill="#C8C8C8"
								r="1.27"
							/>
							<path
								d="M9.701 19.34c.45-.068 1.163-.131 2.254-.131 1 0 1.683.053 2.136.114-.127.48-1.062.664-2.197.664-1.122 0-2.05-.18-2.193-.647z"
								fill="#fff"
							/>
							<path
								d="M11.976 23.099c1.646 0 1.909-1.678 1.96-2.098.039-.34-.137-.511-.33-.627-.191-.116-.768-.224-1.63-.224-.862 0-1.435.108-1.63.224-.196.116-.373.288-.33.627.051.42.314 2.098 1.96 2.098z"
								fill="#838383"
							/>
							<path
								d="M12.934 9.972c-.47-.319-1.143-.348-1.621-.043a4.086 4.086 0 01-2.204.638c-2.217 0-4.014-1.742-4.014-3.89 0-2.149 1.797-3.89 4.014-3.89 1.116 0 2.126.44 2.853 1.154.406.397 1.072.51 1.597.295.407-.167.855-.259 1.324-.259 1.878 0 3.4 1.475 3.4 3.295 0 1.82-1.523 3.295-3.4 3.295-.725 0-1.397-.22-1.95-.595z"
								fill="#C8C8C8"
							/>
							<path
								d="M3.375 9.502a1.31 1.31 0 100-2.62 1.31 1.31 0 000 2.62zM15.702 9.175a1.106 1.106 0 100-2.212 1.106 1.106 0 000 2.212z"
								fill="#4F4F4F"
							/>
						</svg>
					</div>
					<div class=" self-center font-medium">{$i18n.t('Lobe Chat')}</div>
				</button>
			{/if}

			{#if role === 'admin'}
				<button
					class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
					on:click={() => {
						goto('/playground');
						show = false;
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
					<div class=" self-center font-medium">{$i18n.t('Playground')}</div>
				</button>

				<button
					class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
					on:click={() => {
						goto('/admin');
						show = false;
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
					<div class=" self-center font-medium">{$i18n.t('Admin Panel')}</div>
				</button>
			{/if}

			<hr class=" dark:border-gray-800 my-1.5 p-0" />

			<button
				class="flex rounded-md py-2 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={() => {
					localStorage.removeItem('token');
					location.href = '/auth';
					show = false;
				}}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-5 h-5"
					>
						<path
							fill-rule="evenodd"
							d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z"
							clip-rule="evenodd"
						/>
						<path
							fill-rule="evenodd"
							d="M6 10a.75.75 0 01.75-.75h9.546l-1.048-.943a.75.75 0 111.004-1.114l2.5 2.25a.75.75 0 010 1.114l-2.5 2.25a.75.75 0 11-1.004-1.114l1.048-.943H6.75A.75.75 0 016 10z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center font-medium">{$i18n.t('Sign Out')}</div>
			</button>

			{#if $activeUserCount}
				<hr class=" dark:border-gray-800 my-1.5 p-0" />

				<Tooltip
					content={$USAGE_POOL && $USAGE_POOL.length > 0
						? `${$i18n.t('Running')}: ${$USAGE_POOL.join(', ')} ✨`
						: ''}
				>
					<div class="flex rounded-md py-1.5 px-3 text-xs gap-2.5 items-center">
						<div class=" flex items-center">
							<span class="relative flex size-2">
								<span
									class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
								/>
								<span class="relative inline-flex rounded-full size-2 bg-green-500" />
							</span>
						</div>

						<div class=" ">
							<span class=" font-medium">
								{$i18n.t('Active Users')}:
							</span>
							<span class=" font-semibold">
								{$activeUserCount}
							</span>
						</div>
					</div>
				</Tooltip>
			{/if}

			<!-- <DropdownMenu.Item class="flex items-center px-3 py-2 text-sm  font-medium">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item> -->
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
