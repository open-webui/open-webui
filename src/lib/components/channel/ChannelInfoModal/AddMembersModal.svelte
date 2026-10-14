<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	const i18n = getContext<any>('i18n');

	import { addMembersById, inviteAppToChannel } from '$lib/apis/channels';
	import { getApps, type App } from '$lib/apis/apps';
	import { config } from '$lib/stores';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import MemberSelector from '$lib/components/workspace/common/MemberSelector.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let show = false;
	export let channel: any = null;
	export let joinedApps: App[] = [];
	let apps: App[] = [];
	let appIds: string[] = [];
	$: availableApps = apps.filter(
		(app) => app.is_active && !joinedApps.some((joined) => joined.id === app.id)
	);

	export let onUpdate = () => {};

	let groupIds: string[] = [];
	let userIds: string[] = [];

	let loading = false;

	const submitHandler = async () => {
		if (loading) return;
		loading = true;
		let changed = false;
		try {
			if (userIds.length || groupIds.length) {
				await addMembersById(localStorage.token, channel.id, {
					user_ids: userIds,
					group_ids: groupIds
				});
				userIds = [];
				groupIds = [];
				changed = true;
			}
			for (const id of [...appIds]) {
				await inviteAppToChannel(localStorage.token, channel.id, id);
				appIds = appIds.filter((appId) => appId !== id);
				changed = true;
			}
			toast.success($i18n.t('Members added successfully'));
			show = false;
		} catch (error) {
			// Preserve the previous fallback error in the translation catalogs.
			// $i18n.t('Failed to add members');
			toast.error(`${error}`);
		} finally {
			if (changed) onUpdate();
			loading = false;
		}
	};

	let opened = false;
	$: if (show && !opened) {
		opened = true;
		if ($config?.features?.enable_apps && channel?.type !== 'dm') {
			getApps(localStorage.token)
				.then((value) => (apps = value))
				.catch((error) => toast.error(`${error}`));
		}
	} else if (!show) {
		opened = false;
		apps = [];
	}

	const reset = () => {
		userIds = [];
		groupIds = [];
		appIds = [];
		loading = false;
	};

	$: if (!show) {
		reset();
	}
</script>

{#if channel}
	<Modal size="sm" bind:show>
		<div>
			<div class=" flex justify-between dark:text-gray-100 px-4 pt-3 mb-1">
				<div class="self-center text-base">
					<div class="flex items-center gap-0.5 shrink-0">
						{$i18n.t('Add Members')}
					</div>
				</div>
				<button
					class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
					on:click={() => {
						show = false;
					}}
				>
					<XMark className={'size-4'} />
				</button>
			</div>

			<div class="flex flex-col md:flex-row w-full px-3 pb-4 md:space-x-4 dark:text-gray-200">
				<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
					<form
						class="flex flex-col w-full"
						on:submit={(e) => {
							e.preventDefault();
							submitHandler();
						}}
					>
						<div class="flex flex-col w-full h-full pb-2">
							<MemberSelector
								bind:userIds
								bind:groupIds
								bind:appIds
								apps={availableApps}
								includeGroups={channel.type === 'group'}
								includeUsers={channel.type === 'group'}
							/>
						</div>

						<div class="flex justify-end pt-3 text-sm font-normal gap-1.5">
							<button
								class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white disabled:cursor-not-allowed"
								type="submit"
								disabled={loading || !(userIds.length || groupIds.length || appIds.length)}
							>
								{$i18n.t('Add')}

								{#if loading}
									<div class="shrink-0">
										<Spinner className="size-3" />
									</div>
								{/if}
							</button>
						</div>
					</form>
				</div>
			</div>
		</div>
	</Modal>
{/if}
