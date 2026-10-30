<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { config, user, openComments, commentCounts } from '$lib/stores';
	import { isSavedChatId } from '$lib/utils/chatId';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Annotation from '$lib/components/icons/Annotation.svelte';
	import {
		commentsRequest,
		resourceQuery,
		type CommentResource,
		type CommentTarget
	} from '$lib/apis/comments';
	export let resource: CommentResource;
	export let target: CommentTarget = {};
	export let label = 'Comments';
	export let onOpen = () => {};
	export let menu = false;
	export let modal: boolean | undefined = undefined;
	export let className = '';
	export let wrapperClassName = '';
	$: buttonClass =
		className ||
		(menu
			? 'select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-gray-900 dark:hover:text-gray-100'
			: 'inline-flex shrink-0 items-center justify-center p-0 bg-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 transition-colors');
	const i18n = getContext<any>('i18n');
	let requestVersion = 0;
	$: enabled = !!(
		$config?.features?.enable_comments &&
		$user &&
		resource.resource_id &&
		(resource.resource_type !== 'chat' ||
			isSavedChatId(resource.resource_id))
	);
	$: countKey = enabled && !menu ? `${$user.id}:${resourceQuery(resource)}` : '';
	$: count = countKey ? ($commentCounts[countKey] ?? 0) : 0;
	const loadCount = async (key: string) => {
		const version = ++requestVersion;
		if (!key) return;
		const previous = $commentCounts[key];
		try {
			const result = await commentsRequest<{ total: number }>(
				`/?${resourceQuery(resource)}&limit=1`
			);
			if (version === requestVersion && $commentCounts[key] === previous)
				commentCounts.update((counts) => ({ ...counts, [key]: result.total }));
		} catch {
			if (version === requestVersion) commentCounts.update((counts) => ({ ...counts, [key]: 0 }));
		}
	};
	$: loadCount(countKey);
	onDestroy(() => {
		++requestVersion;
	});
</script>

<svelte:window on:focus={() => loadCount(countKey)} />

{#if enabled}
	{#snippet commentButton()}
		<button
			type="button"
			class={buttonClass}
			aria-label={count > 0 ? `${$i18n.t(label)} (${count})` : $i18n.t(label)}
			on:click|stopPropagation={() => {
				onOpen();
				openComments(resource, { ...target, modal });
			}}
			><span class="relative inline-flex shrink-0">
				<Annotation className={menu ? 'size-3.5' : 'size-4'} />
				{#if count > 0}
					<span
						aria-hidden="true"
						class="absolute -top-[3px] -end-[5px] flex h-3 min-w-3 items-center justify-center whitespace-nowrap rounded-full bg-red-500 px-px text-[8px] leading-none font-normal text-white"
						>{count > 99 ? '99+' : count}</span
					>
				{/if}
			</span>{#if menu}{$i18n.t(label)}{/if}</button
		>
	{/snippet}
	{#if menu}
		{@render commentButton()}
	{:else}
		<Tooltip content={$i18n.t(label)} className={`flex ${wrapperClassName}`}>
			{@render commentButton()}
		</Tooltip>
	{/if}
{/if}
