<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { fnStore } from '$lib/apis/functions';
	import i18n from '$lib/i18n';

	let editor: Monaco.editor.IStandaloneCodeEditor;
	let monaco: typeof Monaco;
	let editorContainer: HTMLElement;

	onMount(async () => {
		// Import our 'monaco.ts' file here
		// (onMount() will only be executed in the browser, which is what we want)
		monaco = (await import('$lib/apis/monaco')).default;
		// const schema = {
		// 	arbitraryJs: {
		// 		description: "Runs arbitrary JavaScript code",
		// 		params: {
		// 			code: {
		// 				description:
		// 					"The JavaScript code to run, has to be valid JS code without any text or explanation",
		// 				type: "string",
		// 				required: true,
		// 			},
		// 		},
		// 	},
		// };
		const schema = $fnStore.schema;
		const schemaName: keyof typeof schema = $page.params.function;

		// set font

		monaco.languages.typescript.typescriptDefaults.addExtraLib(
			`const _ = ${JSON.stringify(schema)} as const;
            type StringToType<T extends string> = T extends "string" ? string : T extends "number" ? number : T extends "boolean" ? boolean : T extends "object" ? object : T extends "array" ? any[] : T extends "null" ? null : T extends "undefined" ? undefined : T extends "function" ? Function : T;
            type T = typeof _;
            type Tool = {
			    [K in keyof T]: (params: {
				[P in keyof T[K]["params"]]: StringToType<T[K]["params"][P]["type"]>;
			    }) => any;
            }["${schemaName}"];`,
			'file:///toolType.d.ts'
		);

		// monaco.editor.defineTheme("default", {
		// 	base: "vs-dark",
		// 	inherit: true,
		// 	rules: [
		// 		{
		// 			token: "identifier",
		// 			foreground: "9CDCFE",
		// 		},
		// 		{
		// 			token: "identifier.function",
		// 			foreground: "DCDCAA",
		// 		},
		// 		{
		// 			token: "type",
		// 			foreground: "1AAFB0",
		// 		},
		// 	],
		// 	colors: {},
		// });

		// if the system is dark mode, use the dark theme
		if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
			monaco.editor.setTheme('vs-dark');
		} else {
			monaco.editor.setTheme('vs');
		}

		const _editor = monaco.editor.create(editorContainer, {
			automaticLayout: true,
			fontSize: 24
		});
		_editor.addAction({
			id: 'save',
			label: 'Save AI Tool',
			keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS],
			run: () => {
				const code = _editor.getValue();
				$fnStore.fns[schemaName] = {
					...$fnStore.fns[schemaName],
					fn: code
				};
			}
		});
		_editor.addAction({
			id: 'test',
			label: 'Test AI Tool',
			keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter],
			run: test
		});
		const fns = $fnStore.fns;
		const model = monaco.editor.createModel(fns[schemaName]?.fn, 'typescript');
		_editor.setModel(model);
		editor = _editor;
	});

	onDestroy(() => {
		monaco?.editor.getModels().forEach((model) => model.dispose());
		editor?.dispose();
	});

	const save = () => {
		const code = editor.getValue();
		$fnStore.fns[$page.params.function] = {
			...$fnStore.fns[$page.params.function],
			fn: code
		};
		$fnStore = { ...$fnStore };
	};

	const saveAndGoBack = () => {
		save();
	};

	const test = async () => {
		console.log('transpiling...');
		const codeTs = editor.getValue();
		const typescript = await import('typescript');
		const code = typescript.transpile(codeTs, {
			lib: ['es2022'],
			target: typescript.ScriptTarget.ES2017
		});
		const fn = eval(code);
		const schema = $fnStore.schema;
		const schemaName: keyof typeof schema = $page.params.function;

		// for each parameter, prompt the user for a value
		let params = {};
		if (schema[schemaName]?.params !== undefined) {
			params = Object.keys(schema[schemaName].params).reduce((acc, key) => {
				const param = schema[schemaName].params[key];
				const value = prompt(`${key} (${param.type})`);
				if (value === null) return acc;
				acc[key] =
					param.type === 'number'
						? parseInt(value)
						: param.type === 'boolean'
						? value !== 'false'
						: (value as any);
				return acc;
			}, {} as Record<string, string>);
		}
		console.log('running...');
		const res = await fn(params);
		console.log('result:', res);
	};
</script>

<div>
	<div class="w-screen h-screen" bind:this={editorContainer} />
	<div class="fixed bottom-0 right-0 p-4 px-8 z-50 bg flex gap-4">
		<button
			class="p-2 px-4 flex gap-2 items-center bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition false"
			on:click={test}
		>
			{$i18n.t('Test')}
		</button>
		<a
			href="/"
			style="-webkit-user-drag: none;"
			class="p-2 px-4 flex gap-2 items-center bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition false"
			on:click={saveAndGoBack}
		>
			{$i18n.t('Save and go back')}
		</a>
	</div>
</div>
