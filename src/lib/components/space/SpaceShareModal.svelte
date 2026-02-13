<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { toast } from 'svelte-sonner';

	import {
		inviteContributor,
		removeContributor,
		updateSpaceAccessLevel,
		SpaceAccessLevel,
		SpacePermission
	} from '$lib/apis/spaces';
	import type { Space, SpaceContributor } from '$lib/apis/spaces';
	import { user } from '$lib/stores';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import BulkShareModal from '$lib/components/space/BulkShareModal.svelte';

	export let show = false;
	export let space: Space | null = null;
	export let onUpdate: () => void = () => {};

	let inviteEmail = '';
	let inviteLoading = false;
	let accessLoading = false;
	let copySuccess = false;
	let showBulkShareModal = false;
	let previousAccessLevel: string = '';

	const permissionLabel = (permission: number): string => {
		switch (permission) {
			case SpacePermission.OWNER:
				return 'Owner';
			case SpacePermission.EDITOR:
				return 'Editor';
			case SpacePermission.WRITER:
				return 'Writer';
			case SpacePermission.READER:
				return 'Reader';
			default:
				return 'None';
		}
	};

	const permissionColor = (permission: number): string => {
		switch (permission) {
			case SpacePermission.OWNER:
				return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300';
			case SpacePermission.EDITOR:
				return 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300';
			case SpacePermission.WRITER:
				return 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300';
			case SpacePermission.READER:
				return 'bg-gray-100 text-gray-700 dark:bg-gray-700/40 dark:text-gray-300';
			default:
				return 'bg-gray-100 text-gray-600 dark:bg-gray-700/40 dark:text-gray-400';
		}
	};

	const avatarColor = (str: string): string => {
		const colors = [
			'bg-rose-500',
			'bg-pink-500',
			'bg-fuchsia-500',
			'bg-violet-500',
			'bg-indigo-500',
			'bg-blue-500',
			'bg-sky-500',
			'bg-cyan-500',
			'bg-teal-500',
			'bg-emerald-500',
			'bg-green-500',
			'bg-amber-500'
		];
		let hash = 0;
		for (let i = 0; i < str.length; i++) {
			hash = str.charCodeAt(i) + ((hash << 5) - hash);
		}
		return colors[Math.abs(hash) % colors.length];
	};

	const getInitial = (contributor: SpaceContributor): string => {
		if (contributor.user?.name) {
			return contributor.user.name.charAt(0).toUpperCase();
		}
		return contributor.email.charAt(0).toUpperCase();
	};

	const getDisplayName = (contributor: SpaceContributor): string => {
		return contributor.user?.name ?? contributor.email;
	};

	const getDisplayEmail = (contributor: SpaceContributor): string => {
		return contributor.email;
	};

	const isOwner = (contributor: SpaceContributor): boolean => {
		return contributor.permission === SpacePermission.OWNER;
	};

	const isCurrentUserOwner = (): boolean => {
		if (!space || !$user) return false;
		return space.user_id === $user.id;
	};

	const validateEmail = (email: string): boolean => {
		return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
	};

	const handleInvite = async () => {
		if (!space) return;

		const trimmed = inviteEmail.trim();
		if (!trimmed) {
			toast.error($i18n.t('Please enter an email address'));
			return;
		}

		if (!validateEmail(trimmed)) {
			toast.error($i18n.t('Please enter a valid email address'));
			return;
		}

		inviteLoading = true;

		try {
			const res = await inviteContributor(localStorage.token, space.id, trimmed);
			if (res) {
				toast.success($i18n.t('Invitation sent successfully'));
				inviteEmail = '';
				onUpdate();
			}
		} catch (error) {
			toast.error(String(error));
		}

		inviteLoading = false;
	};

	const handleRemove = async (contributor: SpaceContributor) => {
		if (!space) return;

		try {
			const res = await removeContributor(localStorage.token, space.id, contributor.email);
			if (res) {
				toast.success($i18n.t('Contributor removed'));
				onUpdate();
			}
		} catch (error) {
			toast.error(String(error));
		}
	};

	const handleAccessLevelChange = async (level: string) => {
		if (!space) return;
		previousAccessLevel = space.access_level ?? 'private';
		accessLoading = true;

		try {
			const res = await updateSpaceAccessLevel(localStorage.token, space.id, level);
			if (res) {
				toast.success($i18n.t('Access level updated'));
				onUpdate();
				if (previousAccessLevel === 'private' && (level === 'org' || level === 'public')) {
					showBulkShareModal = true;
				}
			}
		} catch (error) {
			toast.error(String(error));
		}

		accessLoading = false;
	};

	const handleCopyLink = async () => {
		if (!space) return;

		try {
			const url = `${window.location.origin}/spaces/${space.slug ?? space.id}`;
			await navigator.clipboard.writeText(url);
			copySuccess = true;
			toast.success($i18n.t('Link copied to clipboard'));
			setTimeout(() => {
				copySuccess = false;
			}, 2000);
		} catch (error) {
			toast.error($i18n.t('Failed to copy link'));
		}
	};

	$: contributors = (space?.contributors ?? []) as SpaceContributor[];
	$: currentAccessLevel = space?.access_level ?? SpaceAccessLevel.PRIVATE;
</script>

<Modal size="md" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class=" text-lg font-medium self-center">
				{$i18n.t('Share this Space')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col w-full px-5 pb-4 dark:text-gray-200">
			<div class="flex flex-col w-full mt-2">
				<div class="mb-1 text-xs text-gray-500">{$i18n.t('Access Level')}</div>
				<div class="relative">
					<select
						class="w-full text-sm bg-transparent outline-hidden appearance-none pl-7 pr-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 cursor-pointer"
						value={currentAccessLevel}
						disabled={accessLoading || !isCurrentUserOwner()}
						on:change={(e) => {
							handleAccessLevelChange(e.currentTarget.value);
						}}
					>
						<option value={SpaceAccessLevel.PRIVATE} class="bg-gray-50 dark:bg-gray-700">
							{$i18n.t('Private')}
						</option>
						<option value={SpaceAccessLevel.ORG} class="bg-gray-50 dark:bg-gray-700">
							{$i18n.t('Organization')}
						</option>
						<option value={SpaceAccessLevel.PUBLIC} class="bg-gray-50 dark:bg-gray-700">
							{$i18n.t('Public')}
						</option>
					</select>
					<div class="absolute left-2 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500">
						{#if currentAccessLevel === SpaceAccessLevel.PUBLIC}
							<GlobeAlt className="size-4" />
						{:else if currentAccessLevel === SpaceAccessLevel.ORG}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-4"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21"
								/>
							</svg>
						{:else}
							<LockClosed className="size-4" />
						{/if}
					</div>
					{#if accessLoading}
						<div class="absolute right-2 top-1/2 -translate-y-1/2">
							<Spinner className="size-3.5" />
						</div>
					{/if}
				</div>
				<div class="mt-1 text-xs text-gray-400">
					{#if currentAccessLevel === SpaceAccessLevel.PRIVATE}
						{$i18n.t('Only invited contributors can access this space')}
					{:else if currentAccessLevel === SpaceAccessLevel.ORG}
						{$i18n.t('Anyone in your organization can access this space')}
					{:else}
						{$i18n.t('Anyone with the link can access this space')}
					{/if}
				</div>
			</div>

			{#if isCurrentUserOwner()}
				<div class="flex flex-col w-full mt-4">
					<div class="mb-1 text-xs text-gray-500">{$i18n.t('Invite People')}</div>
					<form
						class="flex gap-2"
						on:submit|preventDefault={() => {
							handleInvite();
						}}
					>
						<input
							class="flex-1 text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5"
							type="email"
							bind:value={inviteEmail}
							placeholder={$i18n.t('Enter email address')}
							autocomplete="off"
							disabled={inviteLoading}
						/>
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row items-center {inviteLoading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={inviteLoading}
						>
							{$i18n.t('Invite')}
							{#if inviteLoading}
								<div class="ml-2 self-center">
									<Spinner />
								</div>
							{/if}
						</button>
					</form>
				</div>
			{/if}

			{#if contributors.length > 0}
				<div class="flex flex-col w-full mt-4">
					<div class="mb-2 text-xs text-gray-500">
						{$i18n.t('Contributors')} ({contributors.length})
					</div>
					<div class="flex flex-col gap-1 max-h-48 overflow-y-auto">
						{#each contributors as contributor (contributor.id)}
							<div
								class="flex items-center gap-3 px-2 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition group"
							>
								{#if contributor.user?.profile_image_url}
									<img
										src={contributor.user.profile_image_url}
										alt={getDisplayName(contributor)}
										class="size-8 rounded-full object-cover shrink-0"
									/>
								{:else}
									<div
										class="size-8 rounded-full flex items-center justify-center text-white text-xs font-semibold shrink-0 {avatarColor(
											contributor.email
										)}"
									>
										{getInitial(contributor)}
									</div>
								{/if}

								<div class="flex flex-col min-w-0 flex-1">
									<div class="text-sm font-medium truncate dark:text-gray-100">
										{getDisplayName(contributor)}
									</div>
									{#if contributor.user?.name && contributor.user.name !== contributor.email}
										<div class="text-xs text-gray-400 truncate">
											{getDisplayEmail(contributor)}
										</div>
									{/if}
								</div>

								<div class="flex items-center gap-2 shrink-0">
									{#if !contributor.accepted}
										<span
											class="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300"
										>
											{$i18n.t('Pending')}
										</span>
									{/if}

									<span
										class="text-xs px-2 py-0.5 rounded-full font-medium {permissionColor(
											contributor.permission
										)}"
									>
										{$i18n.t(permissionLabel(contributor.permission))}
									</span>

									{#if isCurrentUserOwner() && !isOwner(contributor)}
										<button
											class="opacity-0 group-hover:opacity-100 transition text-gray-400 hover:text-red-500 dark:hover:text-red-400"
											on:click={() => {
												handleRemove(contributor);
											}}
										>
											<XMark className="size-4" />
										</button>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<div class="flex justify-end pt-4 border-t border-gray-100 dark:border-gray-800 mt-4">
				<button
					class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-black/90 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row items-center gap-1.5 border border-gray-200 dark:border-gray-700"
					on:click={() => {
						handleCopyLink();
					}}
				>
					{#if copySuccess}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="size-3.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m4.5 12.75 6 6 9-13.5"
							/>
						</svg>
						{$i18n.t('Copied')}
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="size-3.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"
							/>
						</svg>
						{$i18n.t('Copy link')}
					{/if}
				</button>
			</div>
		</div>
	</div>
</Modal>

<BulkShareModal
	bind:show={showBulkShareModal}
	{space}
	onComplete={() => {
		onUpdate();
	}}
/>
