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

	import { verifyGitLabConnection } from '$lib/apis/configs';

	export let show = false;
	export let edit = false;

	export let connection = null;
	export let onSubmit: (connection: any) => void;
	export let onDelete: (id: string) => void;

	let id = '';
	let name = '';
	let token = '';

	let owner = '';
	let repo = '';
	let branch = '';
	let includeWiki = false;
	let excludePatterns = '';

	let url = 'https://gitlab.com';
	let isSelfHosted = false;
	let enabled = true;
	let autoSync = false;

	let loading = false;
	let verifying = false;
	let showAdvanced = false;

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
			owner = connection.owner ?? '';
			repo = connection.repo ?? '';
			branch = connection.branch ?? '';
			includeWiki = connection.include_wiki ?? false;
			excludePatterns = connection.exclude_patterns ?? DEFAULT_EXCLUDE_PATTERNS;
			enabled = connection.enabled ?? true;
			autoSync = connection.auto_sync ?? false;
		} else {
			id = '';
			name = '';
			url = 'https://gitlab.com';
			isSelfHosted = false;
			token = '';
			owner = '';
			repo = '';
			branch = '';
			includeWiki = false;
			excludePatterns = DEFAULT_EXCLUDE_PATTERNS;
			enabled = true;
			autoSync = false;
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

	const submitHandler = async () => {
		if (!name) {
			toast.error($i18n.t('Please enter a name'));
			return;
		}

		if (!url) {
			toast.error($i18n.t('Please enter a GitLab URL'));
			return;
		}

		loading = true;

		const conn = {
			id: edit ? id : undefined,
			name,
			url: url.replace(/\/$/, ''),
			token,
			owner,
			repo,
			branch,
			include_wiki: includeWiki,
			exclude_patterns: excludePatterns,
			enabled,
			auto_sync: autoSync
		};

		await onSubmit(conn);

		loading = false;
		show = false;

		init();
	};
</script>

<Modal size="sm" bind:show>
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
							<div class="flex flex-col">
								<div class="flex justify-between mb-0.5">
									<label for="gitlab-owner" class="text-xs text-gray-500">
										{$i18n.t('Owner / Group')}
									</label>
								</div>
								<input
									id="gitlab-owner"
									class="w-full text-sm bg-transparent outline-none placeholder:text-gray-300 dark:placeholder:text-gray-700 border-b border-gray-200 dark:border-gray-700 pb-1"
									type="text"
									bind:value={owner}
									placeholder={$i18n.t('username or group')}
									autocomplete="off"
								/>
								<div class="text-xs text-gray-400 mt-0.5">
									{$i18n.t('Limit sync to repos owned by this user or group')}
								</div>
							</div>

							<div class="flex flex-col">
								<div class="flex justify-between mb-0.5">
									<label for="gitlab-repo" class="text-xs text-gray-500">
										{$i18n.t('Repository')}
									</label>
								</div>
								<input
									id="gitlab-repo"
									class="w-full text-sm bg-transparent outline-none placeholder:text-gray-300 dark:placeholder:text-gray-700 border-b border-gray-200 dark:border-gray-700 pb-1"
									type="text"
									bind:value={repo}
									placeholder={$i18n.t('my-repository')}
									autocomplete="off"
								/>
								<div class="text-xs text-gray-400 mt-0.5">
									{$i18n.t('Sync only this specific repository')}
								</div>
							</div>

							<div class="flex flex-col">
								<div class="flex justify-between mb-0.5">
									<label for="gitlab-branch" class="text-xs text-gray-500">
										{$i18n.t('Branch')}
									</label>
								</div>
								<input
									id="gitlab-branch"
									class="w-full text-sm bg-transparent outline-none placeholder:text-gray-300 dark:placeholder:text-gray-700 border-b border-gray-200 dark:border-gray-700 pb-1"
									type="text"
									bind:value={branch}
									placeholder={$i18n.t('main')}
									autocomplete="off"
								/>
								<div class="text-xs text-gray-400 mt-0.5">
									{$i18n.t('Leave empty to use the repository default branch')}
								</div>
							</div>

							<div class="flex items-center justify-between py-2">
								<div class="text-sm">{$i18n.t('Include Wiki')}</div>
								<Switch bind:state={includeWiki} />
							</div>

							<div class="flex flex-col">
								<div class="flex justify-between mb-0.5">
									<label for="gitlab-exclude" class="text-xs text-gray-500">
										{$i18n.t('Exclude Patterns')}
									</label>
								</div>
								<textarea
									id="gitlab-exclude"
									class="w-full text-sm bg-transparent outline-none placeholder:text-gray-300 dark:placeholder:text-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 resize-none"
									rows="3"
									bind:value={excludePatterns}
									placeholder=".gitignore style patterns..."
								/>
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
