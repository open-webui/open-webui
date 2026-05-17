<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	import { verifyGitLabConnection, browseGitLabProjects, getGitLabProjects } from '$lib/apis/configs';

	export let show = false;
	export let edit = false;

	export let connection = null;
	export let onSubmit: (connection: any) => void;
	export let onDelete: (id: string) => void;

	let id = '';
	let name = '';
	let token = '';

	let url = 'https://gitlab.com';
	let isSelfHosted = false;
	let enabled = true;
	let autoSync = false;

	let loading = false;
	let verifying = false;
	let showAdvanced = false;

	// Project browsing state
	let browsingProjects = false;
	let availableProjects: any[] = [];
	let selectedProjectIds: string[] = [];
	let projectSearchQuery = '';
	let fetchingProjects = false;
	let fetchError = '';
	let showSelectedOnly = false;

	const DEFAULT_EXCLUDE_PATTERNS = `node_modules
.git
__pycache__
.venv
venv
dist
build
.cache
.egg-info
.DS_Store
Thumbs.db`;

	const init = () => {
		if (connection) {
			id = connection.id ?? '';
			name = connection.name ?? '';
			url = connection.url ?? 'https://gitlab.com';
			isSelfHosted = url !== 'https://gitlab.com';
			token = connection.token ?? '';
			selectedProjectIds = connection.selected_projects ?? [];
			enabled = connection.enabled ?? true;
			autoSync = connection.auto_sync ?? false;
			showAdvanced = false;
			browsingProjects = false;
			availableProjects = [];
			fetchError = '';
		} else {
			id = '';
			name = '';
			url = 'https://gitlab.com';
			isSelfHosted = false;
			token = '';
			selectedProjectIds = [];
			enabled = true;
			autoSync = false;
			showAdvanced = false;
			browsingProjects = false;
			availableProjects = [];
			fetchError = '';
		}
	};

	$: if (show) {
		init();
	}

	const verifyConnection = async () => {
		if (!url) {
			toast.error($i18n.t('Please enter a GitLab URL'));
			return;
		}

		if (!token) {
			toast.error($i18n.t('Please enter a personal access token'));
			return;
		}

		verifying = true;
		try {
			const res = await verifyGitLabConnection(localStorage.token, url, token);
			if (res?.status) {
				toast.success($i18n.t('Connection successful'));
			}
		} catch (error) {
			toast.error($i18n.t('Connection failed: {{error}}', { error: error.detail || 'Unknown error' }));
		} finally {
			verifying = false;
		}
	};

	const browseProjects = async () => {
		if (!token) {
			toast.error($i18n.t('Please enter a token first'));
			return;
		}
		if (!url) {
			toast.error($i18n.t('Please enter a URL first'));
			return;
		}

		fetchingProjects = true;
		fetchError = '';
		try {
			let res;
			if (edit && id) {
				res = await getGitLabProjects(localStorage.token, id, 1, '', 100);
			} else {
				res = await browseGitLabProjects(localStorage.token, url, token);
			}
			if (res?.projects) {
				availableProjects = res.projects;
				if (res.selected) {
					selectedProjectIds = Array.from(res.selected);
				}
				browsingProjects = true;
			} else {
				fetchError = $i18n.t('No projects found or failed to fetch');
			}
		} catch (e) {
			fetchError = $i18n.t('Failed to fetch projects. Please verify your token has the api scope.');
		} finally {
			fetchingProjects = false;
		}
	};

	const searchProjects = async () => {
		if (!projectSearchQuery.trim()) {
			browseProjects();
			return;
		}
		fetchingProjects = true;
		fetchError = '';
		try {
			let res;
			if (edit && id) {
				res = await getGitLabProjects(localStorage.token, id, 1, projectSearchQuery, 50);
			} else {
				res = await browseGitLabProjects(localStorage.token, url, token);
				if (res?.projects && projectSearchQuery) {
					const query = projectSearchQuery.toLowerCase();
					res.projects = res.projects.filter(
						(p: any) =>
							p.name?.toLowerCase().includes(query) ||
							p.path_with_namespace?.toLowerCase().includes(query)
					);
				}
			}
			if (res?.projects) {
				availableProjects = res.projects;
			} else {
				fetchError = $i18n.t('No projects found for your search');
			}
		} catch (e) {
			fetchError = $i18n.t('Failed to fetch projects');
		} finally {
			fetchingProjects = false;
		}
	};

	const toggleProjectSelection = (projectId: string) => {
		if (selectedProjectIds.includes(projectId)) {
			selectedProjectIds = selectedProjectIds.filter((pid) => pid !== projectId);
		} else {
			selectedProjectIds = [...selectedProjectIds, projectId];
		}
	};

	const submitHandler = async () => {
		if (!name) {
			toast.error($i18n.t('Please enter a name'));
			return;
		}

		if (!url) {
			toast.error($i18n.t('Please enter a GitLab URL'));
			return;
		}

		if (!token) {
			toast.error($i18n.t('Please enter a personal access token'));
			return;
		}

		loading = true;

		const conn = {
			id: edit ? id : undefined,
			name,
			url: url.replace(/\/$/, ''),
			token,
			selected_projects: selectedProjectIds,
			enabled,
			auto_sync: autoSync
		};

		await onSubmit(conn);

		loading = false;
		show = false;

		init();
	};
</script>

<Modal size="md" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<h1 class="text-lg font-medium font-primary">
				{edit ? $i18n.t('Edit GitLab Connection') : $i18n.t('Add GitLab Connection')}
			</h1>
			<button
				class="self-center"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col w-full px-4 pb-4 dark:text-gray-200">
			<form
				class="flex flex-col w-full"
				on:submit={(e) => {
					e.preventDefault();
					submitHandler();
				}}
			>
				<div class="flex flex-col gap-2 mb-3">
					<!-- Basic connection info -->
					<div class="flex flex-col">
						<div class="flex justify-between mb-0.5">
							<label for="gitlab-name" class="text-xs text-gray-500">
								{$i18n.t('Name')}
							</label>
						</div>
						<input
							id="gitlab-name"
							class="w-full text-sm bg-transparent outline-none placeholder:text-gray-300 dark:placeholder:text-gray-700 border-b border-gray-200 dark:border-gray-700 pb-1"
							type="text"
							bind:value={name}
							placeholder={$i18n.t('My GitLab')}
							autocomplete="off"
							required
						/>
					</div>

					<div class="flex items-center justify-between py-2">
						<div class="text-sm">{$i18n.t('Self-hosted')}</div>
						<Switch
							bind:state={isSelfHosted}
							on:change={() => {
								if (!isSelfHosted) {
									url = 'https://gitlab.com';
								}
							}}
						/>
					</div>

					{#if isSelfHosted}
						<div class="flex flex-col">
							<div class="flex justify-between items-center mb-0.5">
								<label for="gitlab-url" class="text-xs text-gray-500">
									{$i18n.t('GitLab URL')}
								</label>
							</div>
							<input
								id="gitlab-url"
								class="w-full text-sm bg-transparent outline-none placeholder:text-gray-300 dark:placeholder:text-gray-700 border-b border-gray-200 dark:border-gray-700 pb-1"
								type="text"
								bind:value={url}
								placeholder="https://gitlab.example.com"
								autocomplete="off"
								required={isSelfHosted}
							/>
						</div>
					{/if}

					<div class="flex flex-col">
						<div class="flex justify-between items-center mb-0.5">
							<label for="gitlab-token" class="text-xs text-gray-500">
								{$i18n.t('Personal Access Token')}
							</label>
						</div>
						<div class="flex items-center gap-2">
							<SensitiveInput
								bind:value={token}
								placeholder={$i18n.t('glpat-xxxxxxxxxx')}
							/>
							<Tooltip content={$i18n.t('Verify Connection')}>
								<button
									type="button"
									class="p-2 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
									on:click={() => verifyConnection()}
									disabled={verifying}
								>
									{#if verifying}
										<Spinner />
									{:else}
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
												clip-rule="evenodd"
											/>
										</svg>
										{/if}
									</button>
								</Tooltip>
							</div>
							<div class="text-xs text-gray-400 mt-1">
								{$i18n.t('Requires api scope')}
							</div>
						</div>

					<!-- Project Selection -->
					<hr class="border-t border-gray-200 dark:border-gray-700 my-3" />

					<div class="flex flex-col gap-2">
						<div class="flex items-center justify-between">
							<div class="text-sm font-medium">
								{$i18n.t('Projects')}
							</div>
							<button
								type="button"
								class="text-xs px-2.5 py-1 bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 rounded-full transition"
								on:click={() => browseProjects()}
								disabled={fetchingProjects}
							>
								{#if fetchingProjects}
									<Spinner className="size-3" />
								{:else}
									{$i18n.t('Browse Projects')}
								{/if}
							</button>
						</div>

						{#if selectedProjectIds.length > 0}
							<div class="flex flex-wrap gap-1.5">
								{#each selectedProjectIds as pid}
									<div class="flex items-center gap-1 text-xs px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
										<span>{pid}</span>
										<button
											type="button"
											class="hover:text-red-500"
											on:click={() => toggleProjectSelection(pid)}
										>
											×
										</button>
									</div>
								{/each}
							</div>
						{:else}
							<div class="text-xs text-gray-400">
								{$i18n.t('No projects selected. Click "Browse Projects" to choose repositories to sync.')}
							</div>
						{/if}
					</div>

					{#if browsingProjects}
						<div class="flex flex-col gap-2 mt-2 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
							<div class="flex items-center gap-2">
								<div class="flex-1 relative">
									<Search className="size-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
									<input
											type="text"
											class="w-full text-xs bg-transparent outline-none pl-7 pr-2 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg"
											placeholder={$i18n.t('Search projects...')}
											bind:value={projectSearchQuery}
											on:keydown={(e) => {
												if (e.key === 'Enter') {
													searchProjects();
												}
											}}
										/>
								</div>
								<button
										type="button"
										class="text-xs px-2 py-1 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
										on:click={() => searchProjects()}
									>
										{$i18n.t('Search')}
									</button>
								</div>

							<div class="flex items-center justify-between">
								<div class="text-xs text-gray-500">
									{$i18n.t('{{count}} projects found', { count: availableProjects.length })}
								</div>
								<div class="flex items-center gap-1">
									<span class="text-xs text-gray-500">{$i18n.t('Show selected only')}</span>
									<Switch bind:state={showSelectedOnly} />
								</div>
							</div>

							{#if fetchError}
								<div class="text-xs text-red-500 py-2">{fetchError}</div>
							{/if}

							<div class="max-h-64 overflow-y-auto flex flex-col gap-0.5 -mx-1 px-1">
								{#if availableProjects.length > 0}
									{#each availableProjects.filter((p) => !showSelectedOnly || selectedProjectIds.includes(String(p.id))) as project}
										{@const projectId = String(project.id)}
										{@const isSelected = selectedProjectIds.includes(projectId)}
										<button
											type="button"
											class="flex items-center gap-2 w-full text-left px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-sm {isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : ''}"
											on:click={() => toggleProjectSelection(projectId)}
										>
											<div class="flex items-center justify-center w-4 h-4 rounded border {isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-300 dark:border-gray-600'}">
												{#if isSelected}
													<svg class="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
														<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
													</svg>
												{/if}
											</div>
											<div class="flex-1 min-w-0">
												<div class="text-sm truncate">{project.name}</div>
												<div class="text-xs text-gray-500 truncate">{project.path_with_namespace}</div>
											</div>
											{#if project.web_url}
												<a
													href={project.web_url}
													target="_blank"
													class="text-gray-400 hover:text-gray-600"
													on:click={(e) => e.stopPropagation()}
												>
													<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
														<path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
													</svg>
												</a>
											{/if}
										</button>
									{/each}
								{:else if !fetchingProjects}
									<div class="text-xs text-gray-400 text-center py-4">
										{$i18n.t('No projects found')}
									</div>
								{/if}
							</div>

							<div class="flex justify-end pt-2">
								<button
									type="button"
									class="text-xs px-3 py-1.5 bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 rounded-full transition"
									on:click={() => (browsingProjects = false)}
								>
									{$i18n.t('Done')} ({selectedProjectIds.length} {$i18n.t('selected')})
								</button>
							</div>
						</div>
					{/if}

					{#if !edit}
						<hr class="border-t border-gray-200 dark:border-gray-700 my-3" />
						<div class="flex items-center justify-between py-1">
							<div class="text-sm">{$i18n.t('Enabled')}</div>
							<Switch bind:state={enabled} />
						</div>
					{/if}

					<button
						type="button"
						class="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition mt-1"
						on:click={() => (showAdvanced = !showAdvanced)}
					>
						<ChevronDown
							className="size-3 transition-transform {showAdvanced ? 'rotate-180' : ''}"
						/>
						{$i18n.t('Advanced')}
					</button>

					{#if showAdvanced}
						<div class="flex flex-col gap-2 mt-1 pl-2 border-l-2 border-gray-200 dark:border-gray-700">
							<div class="flex items-center justify-between py-2">
								<div class="text-sm">{$i18n.t('Wiki Only')}</div>
								<Switch state={false} />
							</div>
							<div class="flex items-center justify-between py-2">
								<div class="text-sm">{$i18n.t('Include Wiki')}</div>
								<Switch state={false} />
							</div>
							<div class="flex items-center justify-between py-2">
								<div class="text-sm">{$i18n.t('Auto Sync')}</div>
								<Switch bind:state={autoSync} />
							</div>
						</div>
					{/if}
				</div>

				<div class="flex justify-between items-center pt-3 text-sm font-medium">
					<div>
						{#if edit}
							<button
								type="button"
								class="px-1 py-1.5 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:underline transition"
								on:click={() => {
									onDelete(id);
									show = false;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}
					</div>

					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2"
						type="submit"
						disabled={loading}
					>
						{$i18n.t('Save')}
						{#if loading}
							<Spinner />
						{/if}
					</button>
				</div>
			</form>
		</div>
	</div>
</Modal>
