<script>
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getProject, getProposals, createProposal, getMyProfile } from '$lib/apis/marketplace';
	import { mobile, showSidebar, user } from '$lib/stores';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');
	
	let project = null;
	let proposals = [];
	let loaded = false;
	let myRole = 'Client';

	let proposalMessage = '';
	let proposalPrice = null;
	let submitting = false;

	onMount(async () => {
		const projectId = $page.params.id;
		try {
			// Fetch my role to know if I can submit proposals
			const profile = await getMyProfile(localStorage.token).catch(() => null);
			if (profile) myRole = profile.role;

			project = await getProject(localStorage.token, projectId);
			proposals = await getProposals(localStorage.token, projectId);
		} catch (error) {
			console.error("Failed to load project details", error);
		}
		loaded = true;
	});

	const handleProposalSubmit = async () => {
		if (proposalMessage.trim() === '' || !proposalPrice) {
			toast.error($i18n.t('Please provide a message and price.'));
			return;
		}

		submitting = true;
		try {
			const res = await createProposal(localStorage.token, $page.params.id, {
				cover_letter: proposalMessage,
				proposed_rate: Number(proposalPrice)
			});
			if (res) {
				toast.success($i18n.t('Proposal submitted successfully!'));
				proposals = [...proposals, res];
				proposalMessage = '';
				proposalPrice = null;
			}
		} catch (error) {
			toast.error(`Error: ${error}`);
		}
		submitting = false;
	};
</script>

{#if loaded}
	<div
		class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''} max-w-full"
	>
		<nav class="   px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
			<div class=" flex items-center">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
					<div class="">
						<div
							class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium bg-transparent py-1 touch-auto pointer-events-auto"
						>
							<a class="min-w-fit transition text-gray-500 hover:text-gray-800 dark:hover:text-white" href="/projects">
								{$i18n.t('Marketplace')}
							</a>
							<span class="text-gray-500">/</span>
							<span class="min-w-fit text-black dark:text-white">
								{project ? project.title : $i18n.t('Project')}
							</span>
						</div>
					</div>

					<div class=" self-center flex items-center gap-1">
						{#if $user !== undefined && $user !== null}
							<UserMenu
								className="w-[240px]"
								role={$user?.role}
								help={true}
							>
								<button
									class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
									aria-label="User Menu"
								>
									<div class=" self-center">
										<img
											src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
											class="size-6 object-cover rounded-full"
											alt="User profile"
											draggable="false"
										/>
									</div>
								</button>
							</UserMenu>
						{/if}
					</div>
				</div>
			</div>
		</nav>

		<div class=" flex-1 max-h-full overflow-y-auto @container px-4 py-8">
			<div class="max-w-4xl mx-auto">
				{#if project}
					<div class="bg-white dark:bg-gray-850 rounded-2xl p-8 mb-8 border border-gray-100 dark:border-gray-800 shadow-sm">
						<div class="flex justify-between items-start">
							<div>
								<h1 class="text-3xl font-bold dark:text-white mb-2">{project.title}</h1>
								<div class="flex gap-4 text-sm mt-4 text-gray-500">
									<span class="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
										<span class="font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Budget')}:</span> ${project.budget}
									</span>
									<span class="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-lg capitalize">
										<span class="font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Status')}:</span> <span class="text-sky-600 dark:text-sky-400">{project.status}</span>
									</span>
								</div>
							</div>
						</div>
						<hr class="my-6 border-gray-100 dark:border-gray-800"/>
						<h2 class="text-lg font-semibold dark:text-white mb-3">{$i18n.t('Description')}</h2>
						<div class="prose dark:prose-invert max-w-none text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
							{project.description}
						</div>
					</div>

					<!-- Proposals Section -->
					<h2 class="text-2xl font-bold dark:text-white mb-6">{$i18n.t('Proposals')} ({proposals.length})</h2>
					
					<div class="space-y-4 mb-8">
						{#if proposals.length === 0}
							<p class="text-gray-500">{$i18n.t('No proposals yet.')}</p>
						{:else}
							{#each proposals as proposal}
								<div class="p-6 rounded-2xl bg-white dark:bg-gray-850 border border-gray-100 dark:border-gray-800 shadow-sm">
									<div class="flex justify-between items-center mb-4">
										<div class="font-medium dark:text-white flex items-center gap-2">
											{#if proposal.freelancer_id}
												<a
													href="/freelancers/{proposal.freelancer_id}"
													class="bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 px-2 py-1 rounded text-xs transition"
												>
													{$i18n.t('Freelancer Profile')}
												</a>
											{:else}
												<span class="bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded text-xs">Freelancer</span>
											{/if}
										</div>
										<div class="font-bold text-lg dark:text-white">${proposal.proposed_rate ?? proposal.price ?? '-'}</div>
									</div>
									<p class="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{proposal.cover_letter ?? proposal.message ?? ''}</p>
									<div class="mt-4 text-xs font-medium text-gray-400 capitalize">
										<span class="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800">{proposal.status}</span>
									</div>
								</div>
							{/each}
						{/if}
					</div>

					<!-- Submit Proposal -->
					{#if myRole === 'Freelancer' && project.status === 'open'}
						<div class="bg-blue-50 dark:bg-blue-900/20 p-6 rounded-2xl border border-blue-100 dark:border-blue-900/50">
							<h3 class="text-xl font-bold text-blue-900 dark:text-blue-100 mb-4">{$i18n.t('Submit a Proposal')}</h3>
							<form class="space-y-4" on:submit|preventDefault={handleProposalSubmit}>
								<div>
									<label class="block text-sm font-medium text-blue-900 dark:text-blue-200 mb-1" for="message">{$i18n.t('Cover Letter / Message')}</label>
									<textarea
										id="message"
										bind:value={proposalMessage}
										rows="4"
										class="w-full px-4 py-2 rounded-xl border border-blue-200 dark:border-blue-800 bg-white dark:bg-gray-900 text-black dark:text-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
										placeholder="Why are you the best fit for this project?"
										required
									></textarea>
								</div>
								<div class="w-1/3">
									<label class="block text-sm font-medium text-blue-900 dark:text-blue-200 mb-1" for="price">{$i18n.t('Proposed Price (USD)')}</label>
									<input
										type="number"
										id="price"
										bind:value={proposalPrice}
										class="w-full px-4 py-2 rounded-xl border border-blue-200 dark:border-blue-800 bg-white dark:bg-gray-900 text-black dark:text-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
										placeholder="e.g. 450"
										required
									/>
								</div>
								<div class="pt-2">
									<button
										type="submit"
										disabled={submitting}
										class="px-6 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition disabled:opacity-50"
									>
										{submitting ? $i18n.t('Submitting...') : $i18n.t('Submit Proposal')}
									</button>
								</div>
							</form>
						</div>
					{/if}
				{:else}
					<div class="text-center py-12 text-gray-500">
						{$i18n.t('Project not found.')}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
