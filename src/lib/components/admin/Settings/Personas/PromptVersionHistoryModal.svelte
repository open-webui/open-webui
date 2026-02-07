<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import VersionItem from './VersionItem.svelte';

	import type { PersonaPrompt, PromptVersion } from '$lib/apis/prompt-groups';
	import { getPromptVersionHistory, rollbackPromptVersion } from '$lib/apis/prompt-groups';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let prompt: PersonaPrompt;

	let versions: PromptVersion[] = [];
	let loading = false;
	let expandedVersions = new Set<number>();
	let currentVersion: number = 0;

	const loadVersionHistory = async () => {
		loading = true;
		try {
			const token = localStorage.getItem('token') || '';
			versions = await getPromptVersionHistory(token, prompt.command);

			// Sort versions by version number descending (newest first)
			versions.sort((a, b) => b.version - a.version);

			// Current version is the highest version number
			if (versions.length > 0) {
				currentVersion = versions[0].version;
			}

			if (versions.length === 0) {
				toast.info('버전 히스토리가 없습니다.');
			}
		} catch (error: any) {
			console.error('Error loading version history:', error);
			if (error?.status === 503) {
				toast.error('Langfuse가 설정되지 않았습니다.');
			} else if (error?.status === 404) {
				toast.error('프롬프트를 찾을 수 없습니다.');
			} else {
				toast.error('버전 히스토리를 불러오는데 실패했습니다.');
			}
		} finally {
			loading = false;
		}
	};

	const handleRollback = async (event: CustomEvent<number>) => {
		const version = event.detail;

		const confirmed = confirm(
			`버전 v${currentVersion}에서 v${version}로 복원하시겠습니까?\n\n` +
				'복원하면 새로운 버전이 생성됩니다.'
		);

		if (!confirmed) return;

		loading = true;
		try {
			const token = localStorage.getItem('token') || '';
			const result = await rollbackPromptVersion(token, prompt.command, version);

			toast.success(`버전 v${version}으로 복원되었습니다. (새 버전: v${result.new_version})`);

			// Emit refresh event to parent
			dispatch('refresh');

			// Reload version history
			await loadVersionHistory();

			// Close modal
			show = false;
		} catch (error: any) {
			console.error('Error rolling back version:', error);
			if (error?.status === 500) {
				toast.error('Langfuse 통신 오류가 발생했습니다.');
			} else if (error?.status === 404) {
				toast.error('버전을 찾을 수 없습니다.');
			} else {
				toast.error('버전 복원에 실패했습니다.');
			}
		} finally {
			loading = false;
		}
	};

	const handleToggleExpanded = (event: { detail: number }) => {
		const version = event.detail;
		if (expandedVersions.has(version)) {
			expandedVersions.delete(version);
		} else {
			expandedVersions.add(version);
		}
		expandedVersions = expandedVersions; // Trigger reactivity
	};

	// Load version history when modal is shown
	$: if (show && prompt) {
		loadVersionHistory();
	}

	// Reset expanded versions when modal is hidden
	$: if (!show) {
		expandedVersions = new Set();
	}
</script>

<Modal bind:show size="md">
	<div class="flex flex-col h-full">
		<!-- Header -->
		<div class="px-5 py-4 border-b dark:border-gray-700">
			<div class="flex items-center justify-between">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
					버전 히스토리
				</h2>
				<button
					on:click={() => (show = false)}
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition"
					aria-label="닫기"
				>
					<svg
						class="size-5"
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
				{prompt.title} ({prompt.command})
			</p>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto">
			{#if loading}
				<div class="flex items-center justify-center h-64">
					<Spinner className="size-8" />
				</div>
			{:else if versions.length === 0}
				<!-- Empty State -->
				<div class="flex flex-col items-center justify-center h-64 text-center px-4">
					<svg
						class="size-12 text-gray-400 dark:text-gray-600 mb-4"
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="1.5"
							d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-1">
						버전 히스토리가 없습니다
					</h3>
					<p class="text-sm text-gray-500 dark:text-gray-400">
						아직 버전 정보를 사용할 수 없습니다.
					</p>
				</div>
			{:else}
				<!-- Version List -->
				<div class="divide-y dark:divide-gray-700">
					{#each versions as version (version.version)}
						<VersionItem
							{version}
							isCurrent={version.version === currentVersion}
							expanded={expandedVersions.has(version.version)}
							on:rollback={handleRollback}
							on:toggle={handleToggleExpanded}
						/>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="px-5 py-4 border-t dark:border-gray-700 flex justify-end">
			<button
				on:click={() => (show = false)}
				class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md transition"
			>
				닫기
			</button>
		</div>
	</div>
</Modal>
