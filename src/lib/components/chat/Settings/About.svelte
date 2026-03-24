<script lang="ts">
	import { getVersionUpdates } from '$lib/apis';
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { WEBUI_NAME, config, showChangelog } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let ollamaVersion = '';

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});

		console.log(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.log(updateAvailable);
	};

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => {
			return '';
		});

		checkForVersionUpdates();
	});
</script>

<div class="flex flex-col h-full">
	<div class="space-y-4 sm:space-y-6 overflow-y-auto pb-6">
		<!-- Version Information Section -->
		<div class="space-y-3 sm:space-y-4">
			<div>
				<h3 class="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('Version Information')}
				</h3>
				<p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
					Current version and update status
				</p>
			</div>

			<!-- Web UI Version Card -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 sm:p-4">
				<div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4">
					<div class="flex-1">
						<div class="text-xs sm:text-sm font-medium text-gray-900 dark:text-white mb-1">
							{$WEBUI_NAME}
							{$i18n.t('Version')}
						</div>
						<div class="flex flex-col gap-1">
							<div class="flex items-center gap-2 text-xs">
								<Tooltip content={WEBUI_BUILD_HASH}>
									<span class="font-mono text-gray-700 dark:text-gray-300">
										v{WEBUI_VERSION}
									</span>
								</Tooltip>

								<a
									href="https://github.com/open-webui/open-webui/releases/tag/v{version.latest}"
									target="_blank"
									class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
								>
									{updateAvailable === null
										? $i18n.t('Checking for updates...')
										: updateAvailable
											? `(v${version.latest} ${$i18n.t('available!')})`
											: $i18n.t('(latest)')}
								</a>
							</div>

							<button
								class="text-xs text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors text-left w-full sm:w-fit"
								on:click={() => {
									showChangelog.set(true);
								}}
							>
								{$i18n.t("See what's new")} →
							</button>
						</div>
					</div>

					<button
						class="w-full sm:w-auto px-2 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
						on:click={() => {
							checkForVersionUpdates();
						}}
					>
						{$i18n.t('Check for updates')}
					</button>
				</div>
			</div>

			{#if ollamaVersion}
				<!-- Ollama Version Card -->
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 sm:p-4">
					<div class="text-xs sm:text-sm font-medium text-gray-900 dark:text-white mb-1">
						{$i18n.t('Ollama Version')}
					</div>
					<div class="text-xs font-mono text-gray-700 dark:text-gray-300">
						{ollamaVersion ?? 'N/A'}
					</div>
				</div>
			{/if}
		</div>

		<!-- License or Community Section -->
		<div class="space-y-3 sm:space-y-4 pt-2">
			<div>
				<h3 class="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{#if $config?.license_metadata}
						{$i18n.t('License Information')}
					{:else}
						{$i18n.t('Community')}
					{/if}
				</h3>
				<p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
					{#if $config?.license_metadata}
						Your license details
					{:else}
						Join our community channels
					{/if}
				</p>
			</div>

			{#if $config?.license_metadata}
				<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 sm:p-4">
					<div class="flex items-start gap-2 sm:gap-3">
						<div class="flex-shrink-0">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-5 h-5 text-blue-600 dark:text-blue-400"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
								/>
							</svg>
						</div>
						<div class="flex-1">
							<div class="text-xs text-blue-900 dark:text-blue-100">
								{#if !$WEBUI_NAME.includes('Open WebUI')}
									<span class="font-medium">{$WEBUI_NAME}</span> -
								{/if}
								<span class="capitalize">{$config?.license_metadata?.type}</span> license purchased by
								<span class="capitalize font-medium">{$config?.license_metadata?.organization_name}</span>
							</div>
						</div>
					</div>
				</div>
			{:else}
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<div class="flex flex-wrap gap-2">
						<a href="https://discord.gg/5rJgQTnV4s" target="_blank" rel="noopener noreferrer">
							<img
								alt="Discord"
								src="https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white"
								class="h-5"
							/>
						</a>

						<a href="https://twitter.com/OpenWebUI" target="_blank" rel="noopener noreferrer">
							<img
								alt="X (formerly Twitter) Follow"
								src="https://img.shields.io/twitter/follow/OpenWebUI"
								class="h-5"
							/>
						</a>

						<a href="https://github.com/open-webui/open-webui" target="_blank" rel="noopener noreferrer">
							<img
								alt="Github Repo"
								src="https://img.shields.io/github/stars/open-webui/open-webui?style=social&label=Star us on Github"
								class="h-5"
							/>
						</a>
					</div>
				</div>
			{/if}
		</div>

		<!-- Credits Section -->
		<div class="space-y-4 pt-2">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('Credits')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Acknowledgments and attributions
				</p>
			</div>

			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 text-xs text-gray-600 dark:text-gray-400">
				<div class="mb-3">
					{$i18n.t('Created by')}
					<a
						class="text-blue-600 dark:text-blue-400 hover:underline font-medium"
						href="https://github.com/tjbck"
						target="_blank"
						rel="noopener noreferrer"
					>
						Timothy J. Baek
					</a>
				</div>

				<div>
					Emoji graphics provided by
					<a
						href="https://github.com/jdecked/twemoji"
						target="_blank"
						rel="noopener noreferrer"
						class="text-blue-600 dark:text-blue-400 hover:underline"
					>
						Twemoji
					</a>, licensed under
					<a
						href="https://creativecommons.org/licenses/by/4.0/"
						target="_blank"
						rel="noopener noreferrer"
						class="text-blue-600 dark:text-blue-400 hover:underline"
					>
						CC-BY 4.0
					</a>.
				</div>
			</div>
		</div>

		<!-- License Section -->
		<div class="space-y-4 pt-2">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('License')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					BSD 3-Clause License
				</p>
			</div>

			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<pre
					class="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap leading-relaxed">Copyright (c) {new Date().getFullYear()} <a
						href="https://openwebui.com"
						target="_blank"
						rel="noopener noreferrer"
						class="text-blue-600 dark:text-blue-400 hover:underline">Open WebUI (Timothy Jaeryang Baek)</a
					>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.</pre>
			</div>
		</div>
	</div>
</div>

<style>
	/* Custom scrollbar styling */
	::-webkit-scrollbar {
		width: 8px;
		height: 8px;
	}

	::-webkit-scrollbar-track {
		background: transparent;
	}

	::-webkit-scrollbar-thumb {
		background: rgba(156, 163, 175, 0.5);
		border-radius: 4px;
	}

	::-webkit-scrollbar-thumb:hover {
		background: rgba(156, 163, 175, 0.7);
	}

	:global(.dark) ::-webkit-scrollbar-thumb {
		background: rgba(75, 85, 99, 0.5);
	}

	:global(.dark) ::-webkit-scrollbar-thumb:hover {
		background: rgba(75, 85, 99, 0.7);
	}
</style>