<script lang="ts">
	import { getContext } from 'svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
	import variables from '$lib/themes/variables.json';

	const i18n = getContext('i18n');

	const fullThemeSchema = {
		id: 'custom-theme-example',
		name: 'Custom Theme Example',
		description: 'A brief description of the theme.',
		version: '1.0.0',
		author: 'Your Name',
		repository: 'https://github.com/user/repo',
		targetWebUIVersion: '0.6.29',
		base: 'dark',
		emoji: '🎨',
		metaThemeColor: '#000000',
		systemBackgroundImageUrl: '',
		systemBackgroundImageDarken: 0,
		chatBackgroundImageUrl: '',
		chatBackgroundImageDarken: 30,
		variables: variables.reduce((acc, v) => ({ ...acc, [v.name]: v.defaultValue }), {}),
		gradient: {
			enabled: true,
			direction: 45,
			intensity: 100,
			colors: ['#ff0000', '#0000ff']
		},
		tsparticlesConfig: {},
		animationScript: '',
		css: '/* Custom CSS rules go here */',
		sourceUrl:
			'https://raw.githubusercontent.com/open-webui/open-webui/main/src/lib/themes/oled-dark.json',
		codeMirrorTheme: 'abcdef',
		toggles: {
			cssVariables: true,
			customCss: true,
			animationScript: true,
			tsParticles: true,
			gradient: true,
			systemBackgroundImage: true,
			chatBackgroundImage: true
		}
	};
</script>

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
					edit={false}
				/>
			</div>
		</div>
	</Collapsible>
	<Collapsible title="Key Theme Properties" open={false}>
		<div slot="content" class="pt-2">
			<p>
				Here are the main properties you can use to define your theme. For a complete guide, refer
				to the <a
					href="https://github.com/open-webui/open-webui/blob/main/docs/THEMES.md"
					target="_blank"
					class="text-blue-500 hover:underline">full documentation</a
				>.
			</p>
			<ul class="mt-2 list-disc list-inside space-y-1">
				<li>
					<strong>base:</strong> The base theme to inherit styles from. Can be 'light' or 'dark'. Your
					theme will be applied on top of this.
				</li>
				<li>
					<strong>description:</strong> A brief description of the theme.
				</li>
				<li>
					<strong>css:</strong> Add custom CSS rules to style the UI. This is for more advanced styling
					that can't be achieved with variables alone.
				</li>
				<li>
					<strong>variables:</strong> Define custom values for the core CSS variables. This is the primary
					way to change the colors of the UI.
				</li>
				<li>
					<strong>animationScript:</strong> Custom Javascript for canvas-based animations.
				</li>
				<li>
					<strong>tsparticlesConfig:</strong> Configuration for modern
					<a href="https://tsparticles.dev" target="_blank" class="text-blue-500 hover:underline"
						>tsParticles</a
					> animations.
				</li>
				<li>
					<strong>systemBackgroundImageUrl:</strong> URL for the system-wide background image.
				</li>
				<li>
					<strong>systemBackgroundImageDarken:</strong> How much to darken the system background image
					(0-100).
				</li>
				<li>
					<strong>chatBackgroundImageUrl:</strong> URL for the chat-specific background image.
				</li>
				<li>
					<strong>chatBackgroundImageDarken:</strong> How much to darken the chat background image (0-100).
				</li>
			</ul>
		</div>
	</Collapsible>

	<Collapsible title="Animation Resources" open={false}>
		<div slot="content" class="pt-2">
			<p>
				You can create complex particle animations using one of the supported libraries. Use their
				official editors to build your configuration, then paste the exported JSON into the
				corresponding field in the theme editor.
			</p>
			<ul class="mt-2 list-disc list-inside">
				<li>
					<a href="https://particles.js.org/" target="_blank" class="text-blue-500 hover:underline"
						>tsParticles Official Editor & Samples</a
					>
				</li>
			</ul>
		</div>
	</Collapsible>

	<Collapsible title="Available CSS Variables">
		<div slot="content" class="pt-2">
			<p class="text-gray-500">
				Here is a list of all the available CSS variables that you can use to customize your theme.
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
