<style>
:root {
  --color-stroke-dark: #FDFEFE;
}
</style>
<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { createEventDispatcher, getContext, onMount, tick } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import { fade, slide } from 'svelte/transition';

	import { getUsage } from '$lib/apis';
	import { userSignOut } from '$lib/apis/auths';

	import { showSettings, mobile, showSidebar, showShortcuts, user, theme } from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import TooltipButton from '$lib/components/common/TooltipButton.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';
	import Map from '$lib/components/icons/Map.svelte';
	import Keyboard from '$lib/components/icons/Keyboard.svelte';
	import ShortcutsModal from '$lib/components/chat/ShortcutsModal.svelte';
	import Settings from '$lib/components/icons/Settings.svelte';
	import Code from '$lib/components/icons/Code.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';
	import SignOut from '$lib/components/icons/SignOut.svelte';
	import UserSettingsModal from '$lib/components/chat/UserSettingsModal.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let help = false;
	export let className = 'w-[200px]';

	const dispatch = createEventDispatcher();

	let usage = null;
	let showUserSettings = false;

	const getUsageInfo = async () => {
		const res = await getUsage(localStorage.token).catch((error) => {
			console.error('Error fetching usage info:', error);
		});

		if (res) {
			usage = res;
		} else {
			usage = null;
		}
	};

	$: if (show) {
		getUsageInfo();
	}

	const applyTheme = (_theme) => {
		if (_theme === 'dark') {
			document.documentElement.classList.add('dark');
		} else {
			document.documentElement.classList.remove('dark');
		}

		if (typeof window !== 'undefined' && window.applyTheme) {
			window.applyTheme();
		}
	};

	const toggleTheme = () => {
		const currentTheme = $theme;
		const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
		
		theme.set(newTheme);
		localStorage.setItem('theme', newTheme);
		applyTheme(newTheme);
	};

	const getThemeLabel = (themeValue) => {
		return themeValue === 'dark' ? '다크 모드' : '라이트 모드';
	};
</script>

<ShortcutsModal bind:show={$showShortcuts} />
<UserSettingsModal bind:show={showUserSettings} />

<!-- svelte-ignore a11y-no-static-element-interactions -->
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
			class="{className} flex flex-col items-start p-5 gap-2 bg-gray-50 dark:bg-[rgba(113,122,143,0.3)] shadow-[4px_4px_20px_rgba(0,0,0,0.1)] backdrop-blur-[20px] rounded-[20px] rounded-bl-[4px] z-50 text-gray-900 dark:text-white text-sm border-0"
			sideOffset={4}
			side="top"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<!-- Theme Toggle Button -->
			<div class="w-full">
				<TooltipButton
					label={getThemeLabel($theme)}
					variant="toggle"
					on:click={toggleTheme}
				>
					<div slot="icon">
						{#if $theme === 'light'}
							<!-- Sun icon for light mode -->
							<svg
								width="16"
								height="16"
								viewBox="0 0 20 20"
								fill="none"
								xmlns="http://www.w3.org/2000/svg"
							>
								<circle
									cx="10"
									cy="10"
									r="4"
									class="stroke-gray-900 dark:stroke-[var(--color-stroke-dark)]"
									stroke-width="1.5"
								/>
								<path
									d="M10 2V4"
									class="stroke-gray-900 dark:stroke-[var(--color-stroke-dark)]"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
								<path
									d="M10 16V18"
									class="stroke-gray-900 dark:stroke-[var(--color-stroke-dark)]"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
								<path
									d="M18 10H16"
									class="stroke-gray-900 dark:stroke-[var(--color-stroke-dark)]"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
								<path
									d="M4 10H2"
									class="stroke-gray-900 dark:stroke-[var(--color-stroke-dark)]"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
								<path
									d="M15.66 4.34L14.24 5.76"
									class="stroke-gray-900 dark:stroke-[var(--color-stroke-dark)]"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
								<path
									d="M5.76 14.24L4.34 15.66"
									class="stroke-gray-900 dark:stroke-[var(--color-stroke-dark)]"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
								<path
									d="M15.66 15.66L14.24 14.24"
									class="stroke-gray-900 dark:stroke-[var(--color-stroke-dark)]"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
								<path
									d="M5.76 5.76L4.34 4.34"
									class="stroke-gray-900 dark:stroke-[var(--color-stroke-dark)]"
									stroke-width="1.5"
									stroke-linecap="round"
								/>
							</svg>
						{:else}
							<!-- Moon icon for dark mode -->
							<svg
								width="16"
								height="16"
								viewBox="0 0 22 22"
								fill="none"
								xmlns="http://www.w3.org/2000/svg"
							>
								<path
									d="M11.0002 3.66667C7.31833 3.66667 4.3335 6.6515 4.3335 10.3333C4.3335 14.0152 7.31833 17 11.0002 17C14.682 17 17.6668 14.0152 17.6668 10.3333C17.6668 9.99617 17.6442 9.66417 17.6002 9.33883C17.0168 10.2478 16.0127 10.8517 14.8613 10.8517C13.0738 10.8517 11.6252 9.403 11.6252 7.6155C11.6252 6.464 12.2292 5.45983 13.1382 4.87633C12.8128 4.83233 12.4808 4.80967 12.1437 4.80967"
									class="stroke-gray-900 dark:stroke-[var(--color-stroke-dark)]"
									stroke-width="1.5"
									stroke-linecap="round"
									stroke-linejoin="round"
								/>
							</svg>
						{/if}
					</div>
				</TooltipButton>
			</div>

			<!-- Help Button -->
			<TooltipButton
				label="도움말"
				on:click={async () => {
					show = false;
					window.open('https://hanyang.ac.kr', '_blank');
					if ($mobile) {
						await tick();
						showSidebar.set(false);
					}
				}}
			>
				<svg
					slot="icon"
					width="20"
					height="20"
					viewBox="0 0 20 20"
					fill="none"
					xmlns="http://www.w3.org/2000/svg"
				>
					<path
						d="M10 18C14.4183 18 18 14.4183 18 10C18 5.58172 14.4183 2 10 2C5.58172 2 2 5.58172 2 10C2 14.4183 5.58172 18 10 18Z"
						class="stroke-current"
						stroke-width="1.5"
					/>
					<path d="M10 14V14.01" class="stroke-current" stroke-width="2" stroke-linecap="round" />
					<path
						d="M10 11C10 9 11.5 8.5 12 8C12.5 7.5 12.5 6 11.5 5.5C10.5 5 9.5 5.5 9 6"
						class="stroke-current"
						stroke-width="1.5"
						stroke-linecap="round"
					/>
				</svg>
			</TooltipButton>

			<!-- Logout Button -->
			<TooltipButton
				label="로그아웃"
				on:click={async () => {
					const res = await userSignOut();
					user.set(null);
					localStorage.removeItem('token');

					location.href = res?.redirect_url ?? '/auth';
					show = false;
				}}
			>
				<svg
					slot="icon"
					width="20"
					height="20"
					viewBox="0 0 20 20"
					fill="none"
					xmlns="http://www.w3.org/2000/svg"
				>
					<path
						d="M7.5 17.5H4.16667C3.72464 17.5 3.30072 17.3244 2.98816 17.0118C2.67559 16.6993 2.5 16.2754 2.5 15.8333V4.16667C2.5 3.72464 2.67559 3.30072 2.98816 2.98816C3.30072 2.67559 3.72464 2.5 4.16667 2.5H7.5"
						class="stroke-current"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					/>
					<path
						d="M13.3335 14.1667L17.5002 10L13.3335 5.83333"
						class="stroke-current"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					/>
					<path
						d="M17.5 10H7.5"
						class="stroke-current"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					/>
				</svg>
			</TooltipButton>

			<!-- User Settings (Non-Admin) -->
			{#if role !== 'admin'}
				<hr class="border-white/20 my-1 p-0 w-full" />

				<TooltipButton
					label={$i18n.t('Settings')}
					on:click={async () => {
						show = false;
						showUserSettings = true;

						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<svg
						slot="icon"
						width="20"
						height="20"
						viewBox="0 0 20 20"
						fill="none"
						xmlns="http://www.w3.org/2000/svg"
					>
						<path
							d="M10 12.5C11.3807 12.5 12.5 11.3807 12.5 10C12.5 8.61929 11.3807 7.5 10 7.5C8.61929 7.5 7.5 8.61929 7.5 10C7.5 11.3807 8.61929 12.5 10 12.5Z"
							class="stroke-current"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
						/>
						<path
							d="M16.1667 12.5C16.0557 12.7513 16.0226 13.0302 16.0716 13.3005C16.1206 13.5708 16.2495 13.8203 16.4417 14.0167L16.4917 14.0667C16.6466 14.2215 16.7695 14.4053 16.8533 14.6076C16.9372 14.8099 16.9804 15.0268 16.9804 15.2458C16.9804 15.4649 16.9372 15.6817 16.8533 15.8841C16.7695 16.0864 16.6466 16.2702 16.4917 16.425C16.3369 16.5799 16.153 16.7028 15.9507 16.7866C15.7484 16.8705 15.5316 16.9137 15.3125 16.9137C15.0935 16.9137 14.8766 16.8705 14.6743 16.7866C14.472 16.7028 14.2881 16.5799 14.1333 16.425L14.0833 16.375C13.887 16.1828 13.6374 16.0539 13.3671 16.0049C13.0968 15.956 12.818 15.989 12.5667 16.1C12.3203 16.2056 12.1101 16.3813 11.9621 16.6046C11.814 16.8278 11.7347 17.0887 11.7333 17.3558V17.5C11.7333 17.942 11.5577 18.366 11.2452 18.6785C10.9326 18.9911 10.5087 19.1667 10.0667 19.1667C9.62464 19.1667 9.20072 18.9911 8.88816 18.6785C8.57559 18.366 8.4 17.942 8.4 17.5V17.4225C8.39334 17.1477 8.30455 16.8811 8.14431 16.6567C7.98407 16.4323 7.75987 16.2603 7.5 16.1667C7.24869 16.0557 6.96984 16.0226 6.69951 16.0716C6.42919 16.1206 6.17968 16.2495 5.98333 16.4417L5.93333 16.4917C5.77849 16.6466 5.59466 16.7695 5.39233 16.8533C5.19001 16.9372 4.97316 16.9804 4.75417 16.9804C4.53517 16.9804 4.31832 16.9372 4.116 16.8533C3.91368 16.7695 3.72984 16.6466 3.575 16.4917C3.42014 16.3369 3.29723 16.153 3.21336 15.9507C3.12949 15.7484 3.08633 15.5316 3.08633 15.3125C3.08633 15.0935 3.12949 14.8766 3.21336 14.6743C3.29723 14.472 3.42014 14.2881 3.575 14.1333L3.625 14.0833C3.81718 13.887 3.94613 13.6374 3.99511 13.3671C4.0441 13.0968 4.01102 12.818 3.9 12.5667C3.79437 12.3203 3.61867 12.1101 3.39542 11.9621C3.17218 11.814 2.91127 11.7347 2.64417 11.7333H2.5C2.05797 11.7333 1.63405 11.5577 1.32149 11.2452C1.00893 10.9326 0.833333 10.5087 0.833333 10.0667C0.833333 9.62464 1.00893 9.20072 1.32149 8.88816C1.63405 8.57559 2.05797 8.4 2.5 8.4H2.5775C2.85233 8.39334 3.11889 8.30455 3.34331 8.14431C3.56773 7.98407 3.73967 7.75987 3.83333 7.5C3.94435 7.24869 3.97744 6.96984 3.92845 6.69951C3.87946 6.42919 3.75051 6.17968 3.55833 5.98333L3.50833 5.93333C3.35347 5.77849 3.23057 5.59466 3.14669 5.39233C3.06282 5.19001 3.01967 4.97316 3.01967 4.75417C3.01967 4.53517 3.06282 4.31832 3.14669 4.116C3.23057 3.91368 3.35347 3.72984 3.50833 3.575C3.66318 3.42014 3.84701 3.29723 4.04933 3.21336C4.25166 3.12949 4.46851 3.08633 4.6875 3.08633C4.90649 3.08633 5.12335 3.12949 5.32567 3.21336C5.52799 3.29723 5.71182 3.42014 5.86667 3.575L5.91667 3.625C6.11301 3.81718 6.36252 3.94613 6.63285 3.99511C6.90318 4.0441 7.18203 4.01102 7.43333 3.9H7.5C7.74633 3.79437 7.9566 3.61867 8.10464 3.39542C8.25268 3.17218 8.33198 2.91127 8.33333 2.64417V2.5C8.33333 2.05797 8.50893 1.63405 8.82149 1.32149C9.13405 1.00893 9.55797 0.833333 10 0.833333C10.442 0.833333 10.866 1.00893 11.1785 1.32149C11.4911 1.63405 11.6667 2.05797 11.6667 2.5V2.5775C11.668 2.84461 11.7473 3.10551 11.8954 3.32876C12.0434 3.55201 12.2537 3.72771 12.5 3.83333C12.7513 3.94435 13.0302 3.97744 13.3005 3.92845C13.5708 3.87946 13.8203 3.75051 14.0167 3.55833L14.0667 3.50833C14.2215 3.35347 14.4053 3.23057 14.6076 3.14669C14.8099 3.06282 15.0268 3.01967 15.2458 3.01967C15.4649 3.01967 15.6817 3.06282 15.8841 3.14669C16.0864 3.23057 16.2702 3.35347 16.425 3.50833C16.5799 3.66318 16.7028 3.84701 16.7866 4.04933C16.8705 4.25166 16.9137 4.46851 16.9137 4.6875C16.9137 4.90649 16.8705 5.12335 16.7866 5.32567C16.7028 5.52799 16.5799 5.71182 16.425 5.86667L16.375 5.91667C16.1828 6.11301 16.0539 6.36252 16.0049 6.63285C15.956 6.90318 15.989 7.18203 16.1 7.43333V7.5C16.2056 7.74633 16.3813 7.9566 16.6046 8.10464C16.8278 8.25268 17.0887 8.33198 17.3558 8.33333H17.5C17.942 8.33333 18.366 8.50893 18.6785 8.82149C18.9911 9.13405 19.1667 9.55797 19.1667 10C19.1667 10.442 18.9911 10.866 18.6785 11.1785C18.366 11.4911 17.942 11.6667 17.5 11.6667H17.4225C17.1554 11.668 16.8945 11.7473 16.6712 11.8954C16.448 12.0434 16.2723 12.2537 16.1667 12.5Z"
							class="stroke-current"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
						/>
					</svg>
				</TooltipButton>
			{/if}

			<!-- Admin Only Section -->
			{#if role === 'admin'}
				<hr class="border-white/20 my-1 p-0 w-full" />

				<DropdownMenu.Item
					class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition cursor-pointer text-body-4"
					on:click={async () => {
						show = false;

						await showSettings.set(true);

						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<Settings className="w-5 h-5" strokeWidth="1.5" />
					<span class="text-gray-900 dark:text-gray-100">{$i18n.t('Settings')}</span>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition cursor-pointer text-sm"
					on:click={async () => {
						show = false;

						dispatch('show', 'archived-chat');

						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<ArchiveBox className="size-5" strokeWidth="1.5" />
					<span class="text-gray-900 dark:text-gray-100">{$i18n.t('Archived Chats')}</span>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					as="a"
					href="/playground"
					class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition select-none text-sm"
					on:click={async () => {
						show = false;
						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<Code className="size-5" strokeWidth="1.5" />
					<span class="text-gray-900 dark:text-gray-100">{$i18n.t('Playground')}</span>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					as="a"
					href="/admin"
					class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition select-none text-sm"
					on:click={async () => {
						show = false;
						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<UserGroup className="w-5 h-5" strokeWidth="1.5" />
					<span class="text-gray-900 dark:text-gray-100">{$i18n.t('Admin Panel')}</span>
				</DropdownMenu.Item>

				{#if help}
					<hr class="border-white/20 my-1 p-0 w-full" />

					<DropdownMenu.Item
						as="a"
						target="_blank"
						class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition select-none cursor-pointer text-sm"
						id="chat-share-button"
						on:click={() => {
							show = false;
						}}
						href="https://docs.openwebui.com"
					>
						<QuestionMarkCircle className="size-5" />
						<span class="text-gray-900 dark:text-gray-100">{$i18n.t('Documentation')}</span>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						as="a"
						target="_blank"
						class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition select-none cursor-pointer text-sm"
						id="chat-share-button"
						on:click={() => {
							show = false;
						}}
						href="https://github.com/open-webui/open-webui/releases"
					>
						<Map className="size-5" />
						<span class="text-gray-900 dark:text-gray-100">{$i18n.t('Releases')}</span>
					</DropdownMenu.Item>

					<DropdownMenu.Item
						class="flex flex-row items-center p-1 gap-2 w-full h-7 rounded-lg hover:bg-white/10 transition select-none cursor-pointer text-sm"
						on:click={async () => {
							show = false;
							showShortcuts.set(!$showShortcuts);

							if ($mobile) {
								await tick();
								showSidebar.set(false);
							}
						}}
					>
						<Keyboard className="size-5" />
						<span class="text-gray-900 dark:text-gray-100">{$i18n.t('Keyboard shortcuts')}</span>
					</DropdownMenu.Item>
				{/if}

				{#if usage}
					{#if usage?.user_ids?.length > 0}
						<hr class="border-white/20 my-1 p-0 w-full" />

						<Tooltip
							content={usage?.model_ids && usage?.model_ids.length > 0
								? `${$i18n.t('Running')}: ${usage.model_ids.join(', ')} ✨`
								: ''}
						>
							<div
								class="flex rounded-xl py-1 px-3 text-sm gap-2.5 items-center"
								on:mouseenter={() => {
									getUsageInfo();
								}}
							>
								<div class="flex items-center">
									<span class="relative flex size-2">
										<span
											class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
										/>
										<span class="relative inline-flex rounded-full size-2 bg-green-500" />
									</span>
								</div>

								<div>
									<span class="text-gray-900 dark:text-gray-100">
										{$i18n.t('Active Users')}:
									</span>
									<span class="font-semibold text-gray-900 dark:text-gray-100">
										{usage?.user_ids?.length}
									</span>
								</div>
							</div>
						</Tooltip>
					{/if}
				{/if}
			{/if}
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
