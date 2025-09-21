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

<div class="flex flex-col h-full justify-between space-y-3 text-sm mb-6">
	<div class=" space-y-3 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div>
			<div class=" mb-2.5 text-base font-medium flex space-x-2 items-center">
				<div>
					CerebraUI Version
				</div>
			</div>
			<div class="flex w-full justify-between items-center">
				<div class="flex flex-col text-sm text-gray-700 dark:text-gray-200">
					<div class="flex gap-1">
						<span>v.0.0.1</span>
					</div>

					<!-- <button
						class=" underline flex items-center space-x-1 text-sm text-gray-500 dark:text-gray-500"
						on:click={() => {
							showChangelog.set(true);
						}}
					>
						<div>{$i18n.t("See what's new")}</div>
					</button> -->
				</div>

				<!-- <button
					class=" text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-lg font-medium"
					on:click={() => {
						checkForVersionUpdates();
					}}
				>
					{$i18n.t('Check for updates')}
				</button> -->
			</div>
		</div>

		{#if ollamaVersion}
			<hr class=" border-gray-100 dark:border-gray-850" />

			<div>
				<div class=" mb-2.5 text-base font-medium">{$i18n.t('Ollama Version')}</div>
				<div class="flex w-full">
					<div class="flex-1 text-sm text-gray-700 dark:text-gray-200">
						{ollamaVersion ?? 'N/A'}
					</div>
				</div>
			</div>
		{/if}

		<hr class=" border-gray-100 dark:border-gray-850" />

		<!-- <div class="flex space-x-1">
			<a href="https://discord.gg/5rJgQTnV4s" target="_blank">
				<img
					alt="Discord"
					src="https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white"
				/>
			</a>

			<a href="https://twitter.com/OpenWebUI" target="_blank">
				<img
					alt="X (formerly Twitter) Follow"
					src="https://img.shields.io/twitter/follow/OpenWebUI"
				/>
			</a>

			<a href="https://github.com/open-webui/open-webui" target="_blank">
				<img
					alt="Github Repo"
					src="https://img.shields.io/github/stars/open-webui/open-webui?style=social&label=Star us on Github"
				/>
			</a>
		</div> -->

		<!-- CerebraUI Background Story -->
		<div class="mt-4">
			<div class="mb-2.5 text-base font-medium">
				About CerebraUI
			</div>
			<div class="text-sm text-gray-700 dark:text-gray-200 space-y-3 leading-relaxed">
				<p>
					After version v0.6.5, the original project that once stood for "openness and accessibility" suddenly turned to heavy subscriptions and commercialization. Core features were locked behind a paywall, with prices as high as 8k. Many individual developers, students, and research teams were left behind, and the community that once represented a spirit of co-creation began to fracture.
				</p>
				<p>
					When "open" became just a slogan instead of a promise, the community needed a new spark. A group of developers and users came together to bring that spirit back. They rejected feature locks and black-box updates, and instead built a foundation on self-hosting, portability, and auditability—putting control back in the hands of the users.
				</p>
				<p>
					This is how CerebraUI was born. It is not only a response to the past but also a commitment to the future: core features will always remain open-source, self-hostable, and available offline. Roadmaps and budgets will stay transparent, and users can migrate their data and plugins with one click. CerebraUI aims to be a community-governed, truly user-friendly open-source UI project for individuals and small teams.
				</p>
				<p>
					CerebraUI is positioned as "an open, multi-backend, low-barrier, and highly visual AI workspace." Whether it's research and learning with annotations and evaluations, personal productivity with multi-chat and knowledge base management, or team collaboration with roles and audits—CerebraUI provides a stage for all.
				</p>
				<p>
					The name comes from Cerebra (cerebral cortex / thought) + UI (interface), symbolizing both an extension of thinking and a bridge for communication. We believe that when choice returns to the users, and when transparency and freedom form the foundation, CerebraUI will become more than just a tool—it will be a true community creation.
				</p>
			</div>
		</div>

		<div class="mt-2 text-sm text-gray-400 dark:text-gray-500">
			Emoji graphics provided by
			<a href="https://github.com/jdecked/twemoji" target="_blank">Twemoji</a>, licensed under
			<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC-BY 4.0</a>.
		</div>

		<div>
			<pre
				class="text-sm text-gray-400 dark:text-gray-500">Copyright (c) {new Date().getFullYear()} <a
					href="https://openwebui.com"
					target="_blank"
					class="underline">Open WebUI (Timothy Jaeryang Baek)</a
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
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
</pre>
		</div>

		<div class="mt-2 text-sm text-gray-400 dark:text-gray-500">
			{$i18n.t('Created by')}
			<a
				class=" text-gray-500 dark:text-gray-300 font-medium"
				href="https://github.com/tjbck"
				target="_blank">Timothy J. Baek</a
			>
		</div>

		<div class="mt-2 text-sm text-gray-400 dark:text-gray-500">
			Modified and enhanced by CerebraUI Community
		</div>
	</div>
</div>
