<script lang="ts">
import { DropdownMenu } from 'bits-ui';
import { toast } from 'svelte-sonner';
	import { createEventDispatcher, getContext, onMount, tick } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { goto } from '$app/navigation';
	import { fade, slide } from 'svelte/transition';

	import { getUsage } from '$lib/apis';
	import { userSignOut } from '$lib/apis/auths';
import { resetUserWorkflow } from '$lib/apis/workflow';
import { childProfileSync } from '$lib/services/childProfileSync';

	import { showSettings, mobile, showSidebar, showShortcuts, user } from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import QuestionMarkCircle from '$lib/components/icons/QuestionMarkCircle.svelte';
	import Map from '$lib/components/icons/Map.svelte';
	import Keyboard from '$lib/components/icons/Keyboard.svelte';
	import ShortcutsModal from '$lib/components/chat/ShortcutsModal.svelte';
	import Settings from '$lib/components/icons/Settings.svelte';
	import Code from '$lib/components/icons/Code.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';
	import SignOut from '$lib/components/icons/SignOut.svelte';
	import Users from '$lib/components/icons/Users.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let role = '';
	export let help = false;
	export let className = 'max-w-[240px]';

	const dispatch = createEventDispatcher();

	let usage = null;
	let showResetConfirmation = false;
	
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

const handleResetWorkflow = async () => {
		try {
			await resetUserWorkflow(localStorage.token);
			
        // Clear all workflow-related localStorage
        localStorage.removeItem('assignmentStep');
        localStorage.removeItem('assignmentCompleted');
        localStorage.removeItem('instructionsCompleted');
        localStorage.removeItem('moderationScenariosAccessed');
        localStorage.removeItem('unlock_kids');
        localStorage.removeItem('unlock_moderation');
        localStorage.removeItem('unlock_exit');
        localStorage.removeItem('unlock_completion');

        // Explicitly set starting step so sidebar can immediately reflect reset
        localStorage.setItem('assignmentStep', '1');
			
			// Clear child-specific moderation state
        const childId = localStorage.getItem('selectedChildId');
        // Now remove selectedChildId after capturing
        localStorage.removeItem('selectedChildId');
			if (childId) {
				localStorage.removeItem(`moderationScenarioStates_${childId}`);
				localStorage.removeItem(`moderationScenarioTimers_${childId}`);
				localStorage.removeItem(`moderationCurrentScenario_${childId}`);
			}

        // Clear cached child profiles and deselect current child in user settings
        try {
            childProfileSync.clearCache();
            await childProfileSync.setCurrentChildId(null);
        } catch (e) {
            console.warn('Non-fatal: could not clear selected child in settings:', e);
        }
			
        // Notify and broadcast workflow change so layout guards re-evaluate
        window.dispatchEvent(new Event('storage'));
        window.dispatchEvent(new Event('workflow-updated'));
        toast.success('Study restarted. Starting fresh.');

        // Redirect to intro/welcome page (await and hard-redirect fallback)
        try {
            await goto('/');
        } catch (_) {
            window.location.href = '/';
        }
			show = false;
			showResetConfirmation = false;
		} catch (error) {
			console.error('Failed to reset workflow:', error);
        toast.error('Failed to restart. Please try again.');
		}
	};

	$: if (show) {
		getUsageInfo();
	}
</script>

<ShortcutsModal bind:show={$showShortcuts} />

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
			class="w-full {className}  rounded-2xl px-1 py-1  border border-gray-100  dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg text-sm"
			sideOffset={4}
			side="bottom"
			align="start"
			transition={(e) => fade(e, { duration: 100 })}
		>
			<!-- Disabled Settings button -->
			<!--
			<DropdownMenu.Item
				class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition cursor-pointer"
				on:click={async () => {
					show = false;

					await showSettings.set(true);

					if ($mobile) {
						await tick();
						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center mr-3">
					<Settings className="w-5 h-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Settings')}</div>
			</DropdownMenu.Item>
			-->

			<!-- Disabled Archived Chats button -->
			<!--
			<DropdownMenu.Item
				class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition cursor-pointer"
				on:click={async () => {
					show = false;

					dispatch('show', 'archived-chat');

					if ($mobile) {
						await tick();

						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center mr-3">
					<ArchiveBox className="size-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Archived Chats')}</div>
			</DropdownMenu.Item>
			-->

			<!-- Disabled Parent Dashboard button -->
			<!--
			<button
				class="flex rounded-md py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={() => {
					localStorage.setItem('selectedRole', 'parents');
					goto('/parent');
					show = false;

					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			>
				<div class=" self-center mr-3">
					<Users className="w-5 h-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Parent Dashboard')}</div>
			</button>
			-->

			{#if role === 'admin'}
				<DropdownMenu.Item
					as="a"
					href="/playground"
					class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition select-none"
					on:click={async () => {
						show = false;
						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<Code className="size-5" strokeWidth="1.5" />
					</div>
					<div class=" self-center truncate">{$i18n.t('Playground')}</div>
				</DropdownMenu.Item>
				<DropdownMenu.Item
					as="a"
					href="/admin"
					class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition select-none"
					on:click={async () => {
						show = false;
						if ($mobile) {
							await tick();
							showSidebar.set(false);
						}
					}}
				>
					<div class=" self-center mr-3">
						<UserGroup className="w-5 h-5" strokeWidth="1.5" />
					</div>
					<div class=" self-center truncate">{$i18n.t('Admin Panel')}</div>
				</DropdownMenu.Item>
			{/if}

			{#if help}
				<hr class=" border-gray-50 dark:border-gray-800 my-1 p-0" />

				<!-- {$i18n.t('Help')} -->

				{#if $user?.role === 'admin'}
					<DropdownMenu.Item
						as="a"
						target="_blank"
						class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition"
						id="chat-share-button"
						on:click={() => {
							show = false;
						}}
						href="https://docs.openwebui.com"
					>
						<QuestionMarkCircle className="size-5" />
						<div class="flex items-center">{$i18n.t('Documentation')}</div>
					</DropdownMenu.Item>

					<!-- Releases -->
					<DropdownMenu.Item
						as="a"
						target="_blank"
						class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition"
						id="chat-share-button"
						on:click={() => {
							show = false;
						}}
						href="https://github.com/open-webui/open-webui/releases"
					>
						<Map className="size-5" />
						<div class="flex items-center">{$i18n.t('Releases')}</div>
					</DropdownMenu.Item>
				{/if}

				<DropdownMenu.Item
					class="flex gap-2 items-center py-1.5 px-3 text-sm select-none w-full  hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl transition cursor-pointer"
					id="chat-share-button"
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
					<div class="flex items-center">{$i18n.t('Keyboard shortcuts')}</div>
				</DropdownMenu.Item>
			{/if}

			<!-- Restart Study button -->
			<DropdownMenu.Item
				class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={() => {
					showResetConfirmation = true;
					show = false;
				}}
			>
				<div class=" self-center mr-3">
					<ArrowPath className="w-5 h-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center truncate">Restart Study</div>
			</DropdownMenu.Item>

			<hr class=" border-gray-50 dark:border-gray-800 my-1 p-0" />

			<DropdownMenu.Item
				class="flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				on:click={async () => {
					const res = await userSignOut();
					user.set(null);
					localStorage.removeItem('token');

					location.href = res?.redirect_url ?? '/auth';
					show = false;
				}}
			>
				<div class=" self-center mr-3">
					<SignOut className="w-5 h-5" strokeWidth="1.5" />
				</div>
				<div class=" self-center truncate">{$i18n.t('Sign Out')}</div>
			</DropdownMenu.Item>

			<!-- Disabled Active Users section -->
			<!--
			{#if usage}
				{#if usage?.user_ids?.length > 0}
					<hr class=" border-gray-50 dark:border-gray-800 my-1 p-0" />

					<Tooltip
						content={usage?.model_ids && usage?.model_ids.length > 0
							? `${$i18n.t('Running')}: ${usage.model_ids.join(', ')} ✨`
							: ''}
					>
						<div
							class="flex rounded-xl py-1 px-3 text-xs gap-2.5 items-center"
							on:mouseenter={() => {
								getUsageInfo();
							}}
						>
							<div class=" flex items-center">
								<span class="relative flex size-2">
									<span
										class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
									/>
									<span class="relative inline-flex rounded-full size-2 bg-green-500" />
								</span>
							</div>

							<div class=" ">
								<span class="">
									{$i18n.t('Active Users')}:
								</span>
								<span class=" font-semibold">
									{usage?.user_ids?.length}
								</span>
							</div>
						</div>
					</Tooltip>
				{/if}
			{/if}
			-->

			<!-- <DropdownMenu.Item class="flex items-center py-1.5 px-3 text-sm ">
				<div class="flex items-center">Profile</div>
			</DropdownMenu.Item> -->
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>

<!-- Reset Confirmation Modal -->
{#if showResetConfirmation}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={() => showResetConfirmation = false}>
		<div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md mx-4" on:click|stopPropagation>
			<h3 class="text-lg font-semibold mb-4">Restart Study</h3>
			<p class="text-gray-600 dark:text-gray-300 mb-6">
				Are you sure you want to restart the entire study? This will clear all your progress including child profile, moderation scenarios, and exit survey.
			</p>
			<div class="flex gap-3 justify-end">
				<button 
					class="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
					on:click={() => showResetConfirmation = false}
				>
					Cancel
				</button>
				<button 
					class="px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded-lg transition"
					on:click={handleResetWorkflow}
				>
					Start Over
				</button>
			</div>
		</div>
	</div>
{/if}
