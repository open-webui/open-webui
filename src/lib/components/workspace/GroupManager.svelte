<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		addGroupManagerMembers,
		createGroupKnowledge,
		createGroupPrompt,
		createGroupSkill,
		deleteGroupKnowledge,
		deleteGroupManagerMembers,
		deleteGroupPrompt,
		deleteGroupSkill,
		getGroupManagerAssets,
		getGroupManagerMembers,
		getGroupManagerGroups,
		getGroupManagerSkills,
		updateGroupKnowledge,
		updateGroupPrompt,
		updateGroupSkill
	} from '$lib/apis/groupManager';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AssetList from './GroupManager/AssetList.svelte';
	import {
		allGroupManagerRequestsDenied,
		isGroupManagerAuthorizationFailure
	} from '$lib/utils/groupManager';

	const i18n: any = getContext('i18n');
	let groups: any[] = [];
	let groupId = '';
	let tab = 'members';
	let loading = true;
	let denied = false;
	let errorMessage = '';
	let members: any[] = [];
	let assets: any[] = [];
	let skills: any[] = [];
	let memberId = '';
	let knowledgeName = '';
	let knowledgeDescription = '';
	let promptCommand = '';
	let promptName = '';
	let promptContent = '';
	let skillSlug = '';
	let skillName = '';
	let skillContent = '';

	$: activeGroup = groups.find((group) => group.id === groupId);
	$: knowledge = assets.filter((asset) => asset.resource_type === 'knowledge');
	$: prompts = assets.filter((asset) => asset.resource_type === 'prompt');

	const loadGroup = async () => {
		if (!groupId) return;
		loading = true;
		denied = false;
		errorMessage = '';
		try {
			const [memberResult, assetResult, skillResult] = await Promise.allSettled([
				getGroupManagerMembers(localStorage.token, groupId),
				getGroupManagerAssets(localStorage.token, groupId),
				getGroupManagerSkills(localStorage.token, groupId)
			]);
			const results = [memberResult, assetResult, skillResult];
			const successful = results.filter((result) => result.status === 'fulfilled');
			if (successful.length === 0) {
				const errors = results.map((result) => (result as PromiseRejectedResult).reason);
				denied = allGroupManagerRequestsDenied(errors);
				throw errors[0];
			}
			members = memberResult.status === 'fulfilled' ? memberResult.value : [];
			assets = assetResult.status === 'fulfilled' ? assetResult.value : [];
			skills = skillResult.status === 'fulfilled' ? skillResult.value : [];
			if (successful.length < results.length)
				errorMessage = $i18n.t('Some management areas are not available for this group.');
		} catch (error) {
			errorMessage = (error as any)?.message ?? `${error}`;
			if (!denied) toast.error(errorMessage);
		} finally {
			loading = false;
		}
	};

	const run = async (action: () => Promise<any>, message: string) => {
		try {
			await action();
			toast.success(message);
			await loadGroup();
		} catch (error) {
			errorMessage = (error as any)?.message ?? `${error}`;
			toast.error(errorMessage);
		}
	};

	const editKnowledge = (id: string) => {
		const name = prompt($i18n.t('New name'));
		if (name)
			run(
				() => updateGroupKnowledge(localStorage.token, groupId, id, { name }),
				$i18n.t('Knowledge base updated')
			);
	};
	const editPrompt = (id: string) => {
		const name = prompt($i18n.t('New name'));
		if (name)
			run(
				() => updateGroupPrompt(localStorage.token, groupId, id, { name }),
				$i18n.t('Prompt updated')
			);
	};
	const editSkill = (skill: any) => {
		const name = prompt($i18n.t('New name'), skill.name);
		if (name)
			run(
				() => updateGroupSkill(localStorage.token, groupId, skill.id, { name }),
				$i18n.t('Skill updated')
			);
	};

	const load = async () => {
		loading = true;
		try {
			groups = (await getGroupManagerGroups(localStorage.token)) ?? [];
			groupId = groups[0]?.id ?? '';
			if (groupId) await loadGroup();
			else denied = true;
		} catch (error) {
			denied = isGroupManagerAuthorizationFailure(error);
			errorMessage = (error as any)?.message ?? `${error}`;
			if (!isGroupManagerAuthorizationFailure(error)) toast.error(errorMessage);
		} finally {
			loading = false;
		}
	};

	onMount(load);
</script>

<div class="mx-auto flex h-full w-full max-w-5xl flex-col gap-4 px-3 pb-6 sm:px-5">
	<div aria-live="polite" class="sr-only">{errorMessage}</div>
	{#if loading}<div class="flex flex-1 items-center justify-center">
			<Spinner className="size-6" />
		</div>
	{:else if denied}
		<div
			class="m-auto max-w-md rounded-2xl border border-gray-100 p-8 text-center dark:border-gray-800"
		>
			<div class="mb-2 text-base font-medium">{$i18n.t('Group manager access required')}</div>
			<p class="text-sm text-gray-500">
				{$i18n.t(
					'You do not manage any groups, or your manager permissions have not been granted.'
				)}
			</p>
		</div>
	{:else}
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<h1 class="text-lg font-medium">{$i18n.t('Group workspace')}</h1>
				<p class="text-xs text-gray-500">
					{$i18n.t('Manage only members and assets owned by your group.')}
				</p>
			</div>
			<select
				class="rounded-lg bg-transparent px-3 py-2 text-sm ring-1 ring-gray-200 dark:ring-gray-700"
				bind:value={groupId}
				on:change={loadGroup}
				aria-label={$i18n.t('Group')}
			>
				{#each groups as group}<option value={group.id}>{group.name}</option>{/each}
			</select>
		</div>
		{#if errorMessage}<div
				class="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950/30 dark:text-amber-200"
				role="status"
			>
				{errorMessage}
			</div>{/if}
		<nav
			class="flex gap-4 border-b border-gray-100 text-sm dark:border-gray-800"
			aria-label={$i18n.t('Group workspace sections')}
		>
			{#each [['members', 'Members'], ['knowledge', 'Knowledge'], ['prompts', 'Prompts'], ['skills', 'Skills']] as item}<button
					class="border-b-2 px-1 py-2 {tab === item[0]
						? 'border-black dark:border-white'
						: 'border-transparent text-gray-400'}"
					on:click={() => (tab = item[0])}>{$i18n.t(item[1])}</button
				>{/each}
		</nav>

		{#if tab === 'members'}
			<section class="space-y-3">
				<div class="flex gap-2">
					<input
						class="min-w-0 flex-1 rounded-lg bg-transparent px-3 py-2 text-sm ring-1 ring-gray-200 dark:ring-gray-700"
						bind:value={memberId}
						placeholder={$i18n.t('User ID')}
						aria-label={$i18n.t('User ID')}
					/><button
						class="rounded-lg bg-black px-3 py-2 text-xs text-white dark:bg-white dark:text-black"
						disabled={!memberId}
						on:click={() =>
							run(
								() => addGroupManagerMembers(localStorage.token, groupId, [memberId]),
								$i18n.t('Member added')
							)}>{$i18n.t('Add member')}</button
					>
				</div>
				{#if members.length === 0}<p class="py-10 text-center text-sm text-gray-500">
						{$i18n.t('No members found')}
					</p>{:else}<div
						class="divide-y divide-gray-100 rounded-xl border border-gray-100 dark:divide-gray-800 dark:border-gray-800"
					>
						{#each members as member}<div
								class="flex items-center justify-between px-3 py-3 text-sm"
							>
								<span class="font-mono text-xs">{member.user_id}</span><button
									class="text-xs text-red-600 hover:underline"
									on:click={() =>
										run(
											() =>
												deleteGroupManagerMembers(localStorage.token, groupId, [member.user_id]),
											$i18n.t('Member removed')
										)}>{$i18n.t('Remove')}</button
								>
							</div>{/each}
					</div>{/if}
			</section>
		{:else if tab === 'knowledge'}
			<section class="space-y-3">
				<form
					class="grid gap-2 rounded-xl border border-gray-100 p-3 sm:grid-cols-[1fr_1fr_auto] dark:border-gray-800"
					on:submit|preventDefault={() =>
						run(async () => {
							const result = await createGroupKnowledge(localStorage.token, groupId, {
								name: knowledgeName,
								description: knowledgeDescription
							});
							knowledgeName = '';
							knowledgeDescription = '';
							return result;
						}, $i18n.t('Knowledge base created'))}
				>
					<input
						class="rounded-lg bg-transparent px-3 py-2 text-sm ring-1 ring-gray-200 dark:ring-gray-700"
						bind:value={knowledgeName}
						required
						placeholder={$i18n.t('Name')}
					/><input
						class="rounded-lg bg-transparent px-3 py-2 text-sm ring-1 ring-gray-200 dark:ring-gray-700"
						bind:value={knowledgeDescription}
						placeholder={$i18n.t('Description')}
					/><button
						class="rounded-lg bg-black px-3 py-2 text-xs text-white dark:bg-white dark:text-black"
						>{$i18n.t('Create')}</button
					>
				</form>
				<AssetList
					items={knowledge}
					label={$i18n.t('Knowledge bases')}
					onEdit={editKnowledge}
					onDelete={(id: string) =>
						run(
							() => deleteGroupKnowledge(localStorage.token, groupId, id),
							$i18n.t('Knowledge base deleted')
						)}
				/>
			</section>
		{:else if tab === 'prompts'}
			<section class="space-y-3">
				<form
					class="grid gap-2 rounded-xl border border-gray-100 p-3 sm:grid-cols-3 dark:border-gray-800"
					on:submit|preventDefault={() =>
						run(async () => {
							const result = await createGroupPrompt(localStorage.token, groupId, {
								command: promptCommand,
								name: promptName,
								content: promptContent
							});
							promptCommand = '';
							promptName = '';
							promptContent = '';
							return result;
						}, $i18n.t('Prompt created'))}
				>
					<input
						class="rounded-lg bg-transparent px-3 py-2 text-sm ring-1 ring-gray-200 dark:ring-gray-700"
						bind:value={promptCommand}
						required
						placeholder={$i18n.t('Command')}
					/><input
						class="rounded-lg bg-transparent px-3 py-2 text-sm ring-1 ring-gray-200 dark:ring-gray-700"
						bind:value={promptName}
						required
						placeholder={$i18n.t('Name')}
					/><input
						class="rounded-lg bg-transparent px-3 py-2 text-sm ring-1 ring-gray-200 dark:ring-gray-700"
						bind:value={promptContent}
						required
						placeholder={$i18n.t('Content')}
					/><button
						class="rounded-lg bg-black px-3 py-2 text-xs text-white dark:bg-white dark:text-black sm:col-span-3"
						>{$i18n.t('Create prompt')}</button
					>
				</form>
				<AssetList
					items={prompts}
					label={$i18n.t('Prompts')}
					onEdit={editPrompt}
					onDelete={(id: string) =>
						run(
							() => deleteGroupPrompt(localStorage.token, groupId, id),
							$i18n.t('Prompt deleted')
						)}
				/>
			</section>
		{:else}
			<section class="space-y-3">
				<form
					class="grid gap-2 rounded-xl border border-gray-100 p-3 sm:grid-cols-3 dark:border-gray-800"
					on:submit|preventDefault={() =>
						run(
							() =>
								createGroupSkill(localStorage.token, groupId, {
									slug: skillSlug,
									name: skillName,
									content: skillContent
								}),
							$i18n.t('Skill created')
						)}
				>
					<input
						class="rounded-lg bg-transparent px-3 py-2 text-sm ring-1 ring-gray-200 dark:ring-gray-700"
						bind:value={skillSlug}
						required
						placeholder={$i18n.t('Slug')}
					/><input
						class="rounded-lg bg-transparent px-3 py-2 text-sm ring-1 ring-gray-200 dark:ring-gray-700"
						bind:value={skillName}
						required
						placeholder={$i18n.t('Name')}
					/><input
						class="rounded-lg bg-transparent px-3 py-2 text-sm ring-1 ring-gray-200 dark:ring-gray-700"
						bind:value={skillContent}
						placeholder={$i18n.t('Content')}
					/><button
						class="rounded-lg bg-black px-3 py-2 text-xs text-white dark:bg-white dark:text-black sm:col-span-3"
						>{$i18n.t('Create skill')}</button
					>
				</form>
				{#if skills.length === 0}<p class="py-10 text-center text-sm text-gray-500">
						{$i18n.t('No skills found')}
					</p>{:else}<div class="grid gap-3 sm:grid-cols-2">
						{#each skills as skill}<article
								class="rounded-xl border border-gray-100 p-3 dark:border-gray-800"
							>
								<div class="flex items-start justify-between">
									<div>
										<h2 class="text-sm font-medium">{skill.name}</h2>
										<p class="font-mono text-xs text-gray-500">{skill.slug}</p>
									</div>
									<button
										class="text-xs text-red-600 hover:underline"
										on:click={() =>
											run(
												() => deleteGroupSkill(localStorage.token, groupId, skill.id),
												$i18n.t('Skill deleted')
											)}>{$i18n.t('Delete')}</button
									>
								</div>
								<p class="mt-2 line-clamp-2 text-xs text-gray-500">
									{skill.description || skill.content}
								</p>
							</article>{/each}
					</div>{/if}
			</section>
		{/if}
	{/if}
</div>
