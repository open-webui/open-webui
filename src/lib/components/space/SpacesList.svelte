<script lang="ts">
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';

	import { showSidebar, sidebarPinned, user, WEBUI_NAME } from '$lib/stores';
	import { getSpaces, getBookmarkedSpaces, getPinnedSpaces, getTemplates } from '$lib/apis/spaces';
	import type { Space } from '$lib/apis/spaces';

	import Spinner from '$lib/components/common/Spinner.svelte';

	let loading = true;

	let pinnedSpaces: Space[] = [];
	let bookmarkedSpaces: Space[] = [];
	let mySpaces: Space[] = [];
	let sharedSpaces: Space[] = [];
	let templateSpaces: Space[] = [];

	onMount(async () => {
		await loadAllSpaces();
	});

	const loadAllSpaces = async () => {
		loading = true;

		try {
			const [pinnedRes, bookmarkedRes, myRes, sharedRes, templatesRes] = await Promise.all([
				getPinnedSpaces(localStorage.token).catch(() => []),
				getBookmarkedSpaces(localStorage.token).catch(() => []),
				getSpaces(localStorage.token, null, 'private').catch(() => ({ items: [], total: 0 })),
				getSpaces(localStorage.token, null, 'shared').catch(() => ({ items: [], total: 0 })),
				getTemplates(localStorage.token).catch(() => [])
			]);

			pinnedSpaces = pinnedRes;
			bookmarkedSpaces = bookmarkedRes;
			mySpaces = myRes.items;
			sharedSpaces = sharedRes.items;
			templateSpaces = templatesRes;
		} catch (err) {
			console.error('Failed to load spaces:', err);
		}

		loading = false;
	};

	$: totalSpaces =
		pinnedSpaces.length +
		bookmarkedSpaces.length +
		mySpaces.length +
		sharedSpaces.length +
		templateSpaces.length;
</script>

<svelte:head>
	<title>{$i18n.t('Spaces')} | {$WEBUI_NAME}</title>
</svelte:head>

{#if loading}
	<div
		class="h-screen max-h-[100dvh] w-full flex items-center justify-center"
		class:md:max-w-[calc(100%-var(--sidebar-width))]={$sidebarPinned}
	>
		<div class="flex flex-col items-center gap-3">
			<Spinner className="size-6" />
			<span class="text-sm text-gray-400 dark:text-gray-500">{$i18n.t('Loading spaces...')}</span>
		</div>
	</div>
{:else}
	<div
		class="h-screen max-h-[100dvh] w-full flex flex-col"
		class:md:max-w-[calc(100%-var(--sidebar-width))]={$sidebarPinned}
	>
		<div
			class="sticky top-0 z-20 backdrop-blur-xl bg-white/80 dark:bg-gray-900/80 border-b border-gray-100 dark:border-gray-800/50"
		>
			<div class="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
				<div class="flex items-center gap-3">
					<h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						{$i18n.t('Spaces')}
					</h1>
				</div>

				<button
					class="px-3.5 py-1.5 rounded-lg bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-100 transition text-xs font-medium flex items-center gap-1.5"
					on:click={() => goto('/')}
				>
					<svg
						class="size-3.5"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
					</svg>
					{$i18n.t('New Space')}
				</button>
			</div>
		</div>

		<div class="flex-1 overflow-y-auto">
			{#if totalSpaces === 0}
				<div class="flex flex-col items-center justify-center h-full px-4">
					<div class="text-center max-w-sm">
						<div class="text-5xl mb-4">🚀</div>
						<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
							{$i18n.t('No spaces yet')}
						</h2>
						<p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mb-6">
							{$i18n.t(
								'Spaces are focused workspaces with custom instructions, knowledge bases, and shared conversations. Create your first space to get started.'
							)}
						</p>
						<button
							class="px-4 py-2.5 rounded-xl bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-100 transition text-sm font-medium inline-flex items-center gap-2"
							on:click={() => goto('/')}
						>
							<svg
								class="size-4"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
							</svg>
							{$i18n.t('Create your first space')}
						</button>
					</div>
				</div>
			{:else}
				<div class="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-8">
					{#if pinnedSpaces.length > 0}
						<section>
							<div class="flex items-center gap-2 mb-4">
								<svg
									class="size-4 text-amber-500 dark:text-amber-400"
									viewBox="0 0 24 24"
									fill="currentColor"
								>
									<path
										fill-rule="evenodd"
										d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z"
										clip-rule="evenodd"
									/>
								</svg>
								<h2
									class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
								>
									{$i18n.t('Pinned')}
								</h2>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
								{#each pinnedSpaces as space (space.id)}
									<button
										class="group text-left p-4 rounded-xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:border-gray-300 dark:hover:border-gray-600 transition-all"
										on:click={() => goto(`/spaces/${space.slug}`)}
									>
										<div class="flex items-start gap-3">
											{#if space.emoji}
												<span class="text-2xl flex-shrink-0 mt-0.5">{space.emoji}</span>
											{:else}
												<div
													class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 mt-0.5"
												>
													<svg
														class="size-4 text-gray-400 dark:text-gray-500"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
														/>
													</svg>
												</div>
											{/if}
											<div class="min-w-0 flex-1">
												<div class="flex items-center gap-2">
													<h3
														class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-gray-700 dark:group-hover:text-white transition"
													>
														{space.name}
													</h3>
													{#if space.is_template}
														<span
															class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 flex-shrink-0"
														>
															{$i18n.t('Template')}
														</span>
													{/if}
												</div>
												{#if space.description}
													<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
														{space.description}
													</p>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							</div>
						</section>
					{/if}

					{#if bookmarkedSpaces.length > 0}
						<section>
							<div class="flex items-center gap-2 mb-4">
								<svg
									class="size-4 text-accent-500 dark:text-accent-400"
									viewBox="0 0 24 24"
									fill="currentColor"
								>
									<path
										fill-rule="evenodd"
										d="M6.32 2.577a49.255 49.255 0 0 1 11.36 0c1.497.174 2.57 1.46 2.57 2.93V21a.75.75 0 0 1-1.085.67L12 18.089l-7.165 3.583A.75.75 0 0 1 3.75 21V5.507c0-1.47 1.073-2.756 2.57-2.93Z"
										clip-rule="evenodd"
									/>
								</svg>
								<h2
									class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
								>
									{$i18n.t('Bookmarked')}
								</h2>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
								{#each bookmarkedSpaces as space (space.id)}
									<button
										class="group text-left p-4 rounded-xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:border-gray-300 dark:hover:border-gray-600 transition-all"
										on:click={() => goto(`/spaces/${space.slug}`)}
									>
										<div class="flex items-start gap-3">
											{#if space.emoji}
												<span class="text-2xl flex-shrink-0 mt-0.5">{space.emoji}</span>
											{:else}
												<div
													class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 mt-0.5"
												>
													<svg
														class="size-4 text-gray-400 dark:text-gray-500"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
														/>
													</svg>
												</div>
											{/if}
											<div class="min-w-0 flex-1">
												<div class="flex items-center gap-2">
													<h3
														class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-gray-700 dark:group-hover:text-white transition"
													>
														{space.name}
													</h3>
													{#if space.is_template}
														<span
															class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 flex-shrink-0"
														>
															{$i18n.t('Template')}
														</span>
													{/if}
												</div>
												{#if space.description}
													<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
														{space.description}
													</p>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							</div>
						</section>
					{/if}

					<section>
						<div class="flex items-center gap-2 mb-4">
							<svg
								class="size-4 text-gray-400 dark:text-gray-500"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
								/>
							</svg>
							<h2
								class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
							>
								{$i18n.t('My Spaces')}
							</h2>
							<span class="text-xs text-gray-300 dark:text-gray-600">{mySpaces.length}</span>
						</div>
						{#if mySpaces.length === 0}
							<div
								class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 p-8 text-center"
							>
								<p class="text-sm text-gray-400 dark:text-gray-500">
									{$i18n.t("You haven't created any spaces yet.")}
								</p>
							</div>
						{:else}
							<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
								{#each mySpaces as space (space.id)}
									<button
										class="group text-left p-4 rounded-xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:border-gray-300 dark:hover:border-gray-600 transition-all"
										on:click={() => goto(`/spaces/${space.slug}`)}
									>
										<div class="flex items-start gap-3">
											{#if space.emoji}
												<span class="text-2xl flex-shrink-0 mt-0.5">{space.emoji}</span>
											{:else}
												<div
													class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 mt-0.5"
												>
													<svg
														class="size-4 text-gray-400 dark:text-gray-500"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
														/>
													</svg>
												</div>
											{/if}
											<div class="min-w-0 flex-1">
												<div class="flex items-center gap-2">
													<h3
														class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-gray-700 dark:group-hover:text-white transition"
													>
														{space.name}
													</h3>
													{#if space.is_template}
														<span
															class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 flex-shrink-0"
														>
															{$i18n.t('Template')}
														</span>
													{/if}
												</div>
												{#if space.description}
													<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
														{space.description}
													</p>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							</div>
						{/if}
					</section>

					<section>
						<div class="flex items-center gap-2 mb-4">
							<svg
								class="size-4 text-gray-400 dark:text-gray-500"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z"
								/>
							</svg>
							<h2
								class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
							>
								{$i18n.t('Shared with me')}
							</h2>
							<span class="text-xs text-gray-300 dark:text-gray-600">{sharedSpaces.length}</span>
						</div>
						{#if sharedSpaces.length === 0}
							<div
								class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 p-8 text-center"
							>
								<p class="text-sm text-gray-400 dark:text-gray-500">
									{$i18n.t('No shared spaces yet.')}
								</p>
							</div>
						{:else}
							<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
								{#each sharedSpaces as space (space.id)}
									<button
										class="group text-left p-4 rounded-xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:border-gray-300 dark:hover:border-gray-600 transition-all"
										on:click={() => goto(`/spaces/${space.slug}`)}
									>
										<div class="flex items-start gap-3">
											{#if space.emoji}
												<span class="text-2xl flex-shrink-0 mt-0.5">{space.emoji}</span>
											{:else}
												<div
													class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 mt-0.5"
												>
													<svg
														class="size-4 text-gray-400 dark:text-gray-500"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
														/>
													</svg>
												</div>
											{/if}
											<div class="min-w-0 flex-1">
												<div class="flex items-center gap-2">
													<h3
														class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-gray-700 dark:group-hover:text-white transition"
													>
														{space.name}
													</h3>
													{#if space.is_template}
														<span
															class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 flex-shrink-0"
														>
															{$i18n.t('Template')}
														</span>
													{/if}
												</div>
												{#if space.description}
													<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
														{space.description}
													</p>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							</div>
						{/if}
					</section>

					{#if templateSpaces.length > 0}
						<section>
							<div class="flex items-center gap-2 mb-4">
								<svg
									class="size-4 text-violet-500 dark:text-violet-400"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
									/>
								</svg>
								<h2
									class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
								>
									{$i18n.t('Templates')}
								</h2>
								<span class="text-xs text-gray-300 dark:text-gray-600">{templateSpaces.length}</span
								>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
								{#each templateSpaces as space (space.id)}
									<button
										class="group text-left p-4 rounded-xl border border-gray-200 dark:border-gray-700/60 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:border-gray-300 dark:hover:border-gray-600 transition-all"
										on:click={() => goto(`/spaces/${space.slug}`)}
									>
										<div class="flex items-start gap-3">
											{#if space.emoji}
												<span class="text-2xl flex-shrink-0 mt-0.5">{space.emoji}</span>
											{:else}
												<div
													class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0 mt-0.5"
												>
													<svg
														class="size-4 text-gray-400 dark:text-gray-500"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
														/>
													</svg>
												</div>
											{/if}
											<div class="min-w-0 flex-1">
												<div class="flex items-center gap-2">
													<h3
														class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-gray-700 dark:group-hover:text-white transition"
													>
														{space.name}
													</h3>
													<span
														class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 flex-shrink-0"
													>
														{$i18n.t('Template')}
													</span>
												</div>
												{#if space.description}
													<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
														{space.description}
													</p>
												{/if}
											</div>
										</div>
									</button>
								{/each}
							</div>
						</section>
					{/if}
				</div>
			{/if}
		</div>
	</div>
{/if}
