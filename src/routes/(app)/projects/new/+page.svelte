<script>
	import { getContext, onMount } from 'svelte';
	import { createProject } from '$lib/apis/marketplace';
	import { mobile, showSidebar, user } from '$lib/stores';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');
	
	let title = '';
	let description = '';
	let budget = null;
	let status = 'open';

	const submitHandler = async () => {
		if (!title || !description || budget === null) {
			toast.error($i18n.t('Please fill in all fields.'));
			return;
		}

		try {
			const res = await createProject(localStorage.token, {
				title,
				description,
				budget: Number(budget),
				status
			});

			if (res) {
				toast.success($i18n.t('Project posted successfully!'));
				goto('/projects');
			}
		} catch (error) {
			toast.error(`Error: ${error}`);
		}
	};
</script>

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
							{$i18n.t('Post Project')}
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
		<div class="max-w-2xl mx-auto">
			<h1 class="text-2xl font-bold dark:text-white mb-6">{$i18n.t('Post a New Project')}</h1>

			<form class="space-y-6" on:submit|preventDefault={submitHandler}>
				<div>
					<label class="block text-sm font-medium dark:text-gray-300 mb-1" for="title">{$i18n.t('Project Title')}</label>
					<input
						type="text"
						id="title"
						bind:value={title}
						class="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent dark:text-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
						placeholder="e.g. Build an n8n workflow for Notion"
						required
					/>
				</div>

				<div>
					<label class="block text-sm font-medium dark:text-gray-300 mb-1" for="description">{$i18n.t('Description')}</label>
					<textarea
						id="description"
						bind:value={description}
						rows="6"
						class="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent dark:text-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
						placeholder="Describe your project requirements, goals, and technical stack."
						required
					></textarea>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="block text-sm font-medium dark:text-gray-300 mb-1" for="budget">{$i18n.t('Budget (USD)')}</label>
						<input
							type="number"
							id="budget"
							bind:value={budget}
							class="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent dark:text-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
							placeholder="e.g. 500"
							required
						/>
					</div>
					<div>
						<label class="block text-sm font-medium dark:text-gray-300 mb-1" for="status">{$i18n.t('Status')}</label>
						<select
							id="status"
							bind:value={status}
							class="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent dark:text-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
						>
							<option value="open">{$i18n.t('Open')}</option>
							<option value="in_progress">{$i18n.t('In Progress')}</option>
							<option value="closed">{$i18n.t('Closed')}</option>
						</select>
					</div>
				</div>

				<div class="flex justify-end pt-4">
					<button
						type="button"
						class="px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-900 dark:hover:text-white mr-4 transition"
						on:click={() => goto('/projects')}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						type="submit"
						class="px-6 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 rounded-lg transition"
					>
						{$i18n.t('Post Project')}
					</button>
				</div>
			</form>
		</div>
	</div>
</div>
