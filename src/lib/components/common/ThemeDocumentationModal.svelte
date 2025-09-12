<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import variables from '$lib/themes/variables.json';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';

	export let show: boolean;

	const dispatch = createEventDispatcher();

	const cancel = () => {
		dispatch('cancel');
	};

	const fullThemeSchema = {
		id: 'custom-theme-example',
		name: 'Custom Theme Example',
		version: '1.0.0',
		author: 'Your Name',
		repository: 'https://github.com/user/repo',
		targetWebUIVersion: '0.1.124',
		base: 'dark',
		emoji: '🎨',
		metaThemeColor: '#000000',
		variables: variables.reduce((acc, v) => ({ ...acc, [v.name]: v.defaultValue }), {}),
		gradient: {
			enabled: true,
			direction: 45,
			intensity: 100,
			colors: ['#ff0000', '#0000ff']
		},
		particleConfig: {},
		tsparticlesConfig: {},
		animationScript: '',
		css: '/* Custom CSS rules go here */',
		sourceUrl:
			'https://raw.githubusercontent.com/open-webui/open-webui/main/src/lib/themes/oled-dark.json',
		codeMirrorTheme: 'abcdef'
	};
</script>

<Modal bind:show {cancel} width="w-full max-w-4xl">
	<div class="p-4">
		<h2 class="text-lg font-medium">Theme Editor Documentation</h2>

		<div class="mt-4 space-y-4 overflow-y-auto max-h-[70vh] text-sm">
			<Collapsible title="Full Theme Schema" open={false}>
				<div slot="content" class="pt-2">
					<p class="text-gray-500">
						This is the full schema of the JSON file that is acceptable by the theming system.
					</p>
					<div class="mt-2">
						<CodeBlock
							code={JSON.stringify(fullThemeSchema, null, 2)}
							language="json"
							header={false}
							canCopy={true}
						/>
					</div>
				</div>
			</Collapsible>
			<Collapsible title="Key Theme Properties" open={true}>
				<div slot="content" class="pt-2">
					<p>
						Here are the main properties you can use to define your theme. For a complete guide,
						refer to the <a
							href="https://github.com/open-webui/open-webui/blob/main/docs/THEMES.md"
							target="_blank"
							class="text-blue-500 hover:underline">full documentation</a
						>.
					</p>
					<ul class="mt-2 list-disc list-inside space-y-1">
						<li>
							<strong>base:</strong> The base theme to inherit styles from. Can be 'light' or 'dark'.
							Your theme will be applied on top of this.
						</li>
						<li>
							<strong>css:</strong> Add custom CSS rules to style the UI. This is for more advanced
							styling that can't be achieved with variables alone.
						</li>
						<li>
							<strong>variables:</strong> Define custom values for the core CSS variables. This is the
							primary way to change the colors of the UI.
						</li>
						<li>
							<strong>animationScript:</strong> Custom Javascript for canvas-based animations.
						</li>
						<li>
							<strong>particleConfig:</strong> Configuration for legacy
							<a
								href="https://github.com/VincentGarreau/particles.js/"
								target="_blank"
								class="text-blue-500 hover:underline">Particles.js</a
							> animations.
						</li>
						<li>
							<strong>tsparticlesConfig:</strong> Configuration for modern
							<a
								href="https://particles.js.org"
								target="_blank"
								class="text-blue-500 hover:underline">tsParticles</a
							> animations.
						</li>
					</ul>
				</div>
			</Collapsible>

			<Collapsible title="Animation Resources" open={true}>
				<div slot="content" class="pt-2">
					<p>
						You can create complex particle animations using one of the supported libraries. Use
						their official editors to build your configuration, then paste the exported JSON into the
						corresponding field in the theme editor.
					</p>
					<ul class="mt-2 list-disc list-inside">
						<li>
							<a
								href="https://particles.js.org/samples/index.html"
								target="_blank"
								class="text-blue-500 hover:underline">tsParticles Official Editor & Samples</a
							>
						</li>
						<li>
							<a
								href="https://vincentgarreau.com/particles.js/"
								target="_blank"
								class="text-blue-500 hover:underline">Legacy particles.js Demos & Configs</a
							>
						</li>
					</ul>
				</div>
			</Collapsible>

			<Collapsible title="Available CSS Variables">
				<div slot="content" class="pt-2">
					<p class="text-gray-500">
						Here is a list of all the available CSS variables that you can use to customize your
						theme.
					</p>

					<div class="mt-4 overflow-y-auto max-h-96">
						<table class="w-full text-sm text-left">
							<thead
								class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400"
							>
								<tr>
									<th scope="col" class="px-6 py-3"> Variable </th>
									<th scope="col" class="px-6 py-3"> Default Value </th>
									<th scope="col" class="px-6 py-3"> Description </th>
								</tr>
							</thead>
							<tbody>
								{#each variables as variable}
									<tr class="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
										<td class="px-6 py-4 font-mono"> {variable.name} </td>
										<td class="px-6 py-4 font-mono"> {variable.defaultValue} </td>
										<td class="px-6 py-4"> {variable.description} </td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			</Collapsible>
		</div>

		<div class="mt-6 flex justify-end space-x-2">
			<button
				class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 transition rounded-full"
				on:click={cancel}
			>
				Close
			</button>
		</div>
	</div>
</Modal>
