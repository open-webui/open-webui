<script lang="ts">
	import { colord, extend } from 'colord';
	import namesPlugin from 'colord/plugins/names';
	import ColorPicker from 'svelte-awesome-color-picker';
	import { basicSetup, EditorView } from 'codemirror';
	import { keymap, placeholder, Decoration, ViewPlugin } from '@codemirror/view';
	import { Compartment, EditorState } from '@codemirror/state';
	import { WidgetType } from '@codemirror/view';

	extend([namesPlugin]);

	class ColorSwatchWidget extends WidgetType {
		constructor(readonly color: string) {
			super();
		}

		eq(other: ColorSwatchWidget) {
			return other.color === this.color;
		}

		toDOM() {
			const swatch = document.createElement('span');
			swatch.className = 'cm-color-swatch';
			swatch.style.display = 'inline-block';
			swatch.style.width = '1em';
			swatch.style.height = '1em';
			swatch.style.backgroundColor = this.color;
			swatch.style.marginLeft = '0.5em';
			swatch.style.border = '1px solid #ccc';
			swatch.style.cursor = 'pointer';
			return swatch;
		}

		ignoreEvent() {
			return false;
		}
	}

	let originalColorFormat = 'hex';

	const colorSwatchPlugin = ViewPlugin.fromClass(
		class {
			decorations;

			constructor(view) {
				this.decorations = this.getDecorations(view);
			}

			update(update) {
				if (update.docChanged || update.viewportChanged) {
					this.decorations = this.getDecorations(update.view);
				}
			}

			getDecorations(view) {
				const widgets = [];
				const colorRegex =
					/(?:#(?:[0-9a-fA-F]{3,4}){1,2}\b|rgba?\([\d\s,.\/]+\)|hsla?\([\d\s,.\/%degturnrad]+\)|\b(?:aliceblue|antiquewhite|aqua|aquamarine|azure|beige|bisque|black|blanchedalmond|blue|blueviolet|brown|burlywood|cadetblue|chartreuse|chocolate|coral|cornflowerblue|cornsilk|crimson|cyan|darkblue|darkcyan|darkgoldenrod|darkgray|darkgreen|darkgrey|darkkhaki|darkmagenta|darkolivegreen|darkorange|darkorchid|darkred|darksalmon|darkseagreen|darkslateblue|darkslategray|darkslategrey|darkturquoise|darkviolet|deeppink|deepskyblue|dimgray|dimgrey|dodgerblue|firebrick|floralwhite|forestgreen|fuchsia|gainsboro|ghostwhite|gold|goldenrod|gray|green|greenyellow|grey|honeydew|hotpink|indianred|indigo|ivory|khaki|lavender|lavenderblush|lawngreen|lemonchiffon|lightblue|lightcoral|lightcyan|lightgoldenrodyellow|lightgray|lightgreen|lightgrey|lightpink|lightsalmon|lightseagreen|lightskyblue|lightslategray|lightslategrey|lightsteelblue|lightyellow|lime|limegreen|linen|magenta|maroon|mediumaquamarine|mediumblue|mediumorchid|mediumpurple|mediumseagreen|mediumslateblue|mediumspringgreen|mediumturquoise|mediumvioletred|midnightblue|mintcream|mistyrose|moccasin|navajowhite|navy|oldlace|olive|olivedrab|orange|orangered|orchid|palegoldenrod|palegreen|paleturquoise|palevioletred|papayawhip|peachpuff|peru|pink|plum|powderblue|purple|red|rosybrown|royalblue|saddlebrown|salmon|sandybrown|seagreen|seashell|sienna|silver|skyblue|slateblue|slategray|slategrey|snow|springgreen|steelblue|tan|teal|thistle|tomato|turquoise|violet|wheat|white|whitesmoke|yellow|yellowgreen)\b)/gi;

				for (const { from, to } of view.visibleRanges) {
					const text = view.state.doc.sliceString(from, to);
					let match;
					while ((match = colorRegex.exec(text))) {
						const colorStr = match[0];
						const color = colord(colorStr);

						if (color.isValid()) {
							const start = from + match.index;
							const end = start + colorStr.length;
							const deco = Decoration.widget({
								widget: new ColorSwatchWidget(color.toRgbString()),
								side: 1
							});
							widgets.push(deco.range(end));
						}
					}
				}
				return Decoration.set(widgets);
			}
		},
		{
			decorations: (v) => v.decorations,
			eventHandlers: {
				mousedown: (e, view) => {
					const target = e.target as HTMLElement;
					if (target.classList.contains('cm-color-swatch')) {
						e.preventDefault();
						e.stopPropagation();

						const pos = view.posAtDOM(target);
						const text = view.state.doc.sliceString(0, pos);
						const colorRegex =
							/(?:#(?:[0-9a-fA-F]{3,4}){1,2}\b|rgba?\([\d\s,.\/]+\)|hsla?\([\d\s,.\/%degturnrad]+\)|\b(?:aliceblue|antiquewhite|aqua|aquamarine|azure|beige|bisque|black|blanchedalmond|blue|blueviolet|brown|burlywood|cadetblue|chartreuse|chocolate|coral|cornflowerblue|cornsilk|crimson|cyan|darkblue|darkcyan|darkgoldenrod|darkgray|darkgreen|darkgrey|darkkhaki|darkmagenta|darkolivegreen|darkorange|darkorchid|darkred|darksalmon|darkseagreen|darkslateblue|darkslategray|darkslategrey|darkturquoise|darkviolet|deeppink|deepskyblue|dimgray|dimgrey|dodgerblue|firebrick|floralwhite|forestgreen|fuchsia|gainsboro|ghostwhite|gold|goldenrod|gray|green|greenyellow|grey|honeydew|hotpink|indianred|indigo|ivory|khaki|lavender|lavenderblush|lawngreen|lemonchiffon|lightblue|lightcoral|lightcyan|lightgoldenrodyellow|lightgray|lightgreen|lightgrey|lightpink|lightsalmon|lightseagreen|lightskyblue|lightslategray|lightslategrey|lightsteelblue|lightyellow|lime|limegreen|linen|magenta|maroon|mediumaquamarine|mediumblue|mediumorchid|mediumpurple|mediumseagreen|mediumslateblue|mediumspringgreen|mediumturquoise|mediumvioletred|midnightblue|mintcream|mistyrose|moccasin|navajowhite|navy|oldlace|olive|olivedrab|orange|orangered|orchid|palegoldenrod|palegreen|paleturquoise|palevioletred|papayawhip|peachpuff|peru|pink|plum|powderblue|purple|red|rosybrown|royalblue|saddlebrown|salmon|sandybrown|seagreen|seashell|sienna|silver|skyblue|slateblue|slategray|slategrey|snow|springgreen|steelblue|tan|teal|thistle|tomato|turquoise|violet|wheat|white|whitesmoke|yellow|yellowgreen)\b)$/i;

						const match = text.match(colorRegex);

						if (match) {
							const color = match[0];
							const from = pos - color.length;
							const to = pos;

							if (color.startsWith('#')) {
								originalColorFormat = 'hex';
							} else if (color.startsWith('rgb')) {
								originalColorFormat = 'rgb';
							} else if (color.startsWith('hsl')) {
								originalColorFormat = 'hsl';
							} else {
								originalColorFormat = 'name';
							}

							activeColorRange = { from, to };

							pickerColor = colord(color).toHex();
							pickerStyle = `position: fixed; left: ${e.clientX}px; top: ${e.clientY}px; z-index: 9999;`;
							pickerUpdateCallback = (newColor) => {
								if (activeColorRange) {
									let newColorStr = newColor;

									if (originalColorFormat === 'rgb') {
										newColorStr = colord(newColor).toRgbString();
									} else if (originalColorFormat === 'hsl') {
										newColorStr = colord(newColor).toHslString();
									} else if (originalColorFormat === 'name') {
										const named = colord(newColor).toName({ closest: true });
										if (named) {
											newColorStr = named;
										}
									}

									view.dispatch({
										changes: {
											from: activeColorRange.from,
											to: activeColorRange.to,
											insert: newColorStr
										}
									});
									activeColorRange.to = activeColorRange.from + newColorStr.length;
								}
							};
							showPicker = true;
							ignoreNextClick = true;
						}
					}
				}
			}
		}
	);

	import { acceptCompletion } from '@codemirror/autocomplete';
	import { indentWithTab } from '@codemirror/commands';

	import { indentUnit, LanguageDescription } from '@codemirror/language';
	import { languages } from '@codemirror/language-data';

	import { onMount, createEventDispatcher, getContext, tick, onDestroy } from 'svelte';

	import PyodideWorker from '$lib/workers/pyodide.worker?worker';

	import { formatPythonCode } from '$lib/apis/utils';
	import { toast } from 'svelte-sonner';
	import { user, codeMirrorTheme } from '$lib/stores';
	import * as themes from '@uiw/codemirror-themes-all';
	import { oneDark } from '@codemirror/theme-one-dark';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let boilerplate = '';
	export let value = '';

	export let onSave = () => {};
	export let onChange = () => {};

	let _value = '';

	let showPicker = false;
	let pickerStyle = '';
	let pickerColor = '#000000';
	let pickerUpdateCallback = (newColor) => {};
	let activeColorRange = null;
	let ignoreNextClick = false;

	$: if (showPicker && pickerColor) {
		pickerUpdateCallback(pickerColor);
	}

	$: if (value) {
		updateValue();
	}

	const updateValue = () => {
		if (_value !== value) {
			const changes = findChanges(_value, value);
			_value = value;

			if (codeEditor && changes.length > 0) {
				codeEditor.dispatch({ changes });
			}
		}
	};

	/**
	 * Finds multiple diffs in two strings and generates minimal change edits.
	 */
	function findChanges(oldStr: string, newStr: string) {
		// Find the start of the difference
		let start = 0;
		while (start < oldStr.length && start < newStr.length && oldStr[start] === newStr[start]) {
			start++;
		}
		// If equal, nothing to change
		if (oldStr === newStr) return [];
		// Find the end of the difference by comparing backwards
		let endOld = oldStr.length,
			endNew = newStr.length;
		while (endOld > start && endNew > start && oldStr[endOld - 1] === newStr[endNew - 1]) {
			endOld--;
			endNew--;
		}
		return [
			{
				from: start,
				to: endOld,
				insert: newStr.slice(start, endNew)
			}
		];
	}

	export let id = '';
	export let lang = '';

	let codeEditor;

	export const focus = () => {
		codeEditor.focus();
	};

	let isDarkMode = false;
	let editorTheme = new Compartment();
	let editorLanguage = new Compartment();

	languages.push(
		LanguageDescription.of({
			name: 'HCL',
			extensions: ['hcl', 'tf'],
			load() {
				return import('codemirror-lang-hcl').then((m) => m.hcl());
			}
		})
	);
	languages.push(
		LanguageDescription.of({
			name: 'Elixir',
			extensions: ['ex', 'exs'],
			load() {
				return import('codemirror-lang-elixir').then((m) => m.elixir());
			}
		})
	);

	const getLang = async () => {
		const language = languages.find((l) => l.alias.includes(lang));
		return await language?.load();
	};

	let pyodideWorkerInstance = null;

	const getPyodideWorker = () => {
		if (!pyodideWorkerInstance) {
			pyodideWorkerInstance = new PyodideWorker(); // Your worker constructor
		}
		return pyodideWorkerInstance;
	};

	// Generate unique IDs for requests
	let _formatReqId = 0;

	const formatPythonCodePyodide = (code) => {
		return new Promise((resolve, reject) => {
			const id = `format-${++_formatReqId}`;
			let timeout;
			const worker = getPyodideWorker();

			const startTag = `--||CODE-START-${id}||--`;
			const endTag = `--||CODE-END-${id}||--`;

			const script = `
import black
print("${startTag}")
print(black.format_str("""${code.replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/"/g, '\\"')}""", mode=black.Mode()))
print("${endTag}")
`;

			const packages = ['black'];

			function handleMessage(event) {
				const { id: eventId, stdout, stderr } = event.data;
				if (eventId !== id) return; // Only handle our message
				clearTimeout(timeout);
				worker.removeEventListener('message', handleMessage);
				worker.removeEventListener('error', handleError);

				if (stderr) {
					reject(stderr);
				} else {
					function extractBetweenDelimiters(stdout, start, end) {
						console.log('stdout', stdout);
						const startIdx = stdout.indexOf(start);
						const endIdx = stdout.indexOf(end, startIdx + start.length);
						if (startIdx === -1 || endIdx === -1) return null;
						return stdout.slice(startIdx + start.length, endIdx).trim();
					}

					const formatted = extractBetweenDelimiters(
						stdout && typeof stdout === 'string' ? stdout : '',
						startTag,
						endTag
					);

					resolve({ code: formatted });
				}
			}

			function handleError(event) {
				clearTimeout(timeout);
				worker.removeEventListener('message', handleMessage);
				worker.removeEventListener('error', handleError);
				reject(event.message || 'Pyodide worker error');
			}

			worker.addEventListener('message', handleMessage);
			worker.addEventListener('error', handleError);

			// Send to worker
			worker.postMessage({ id, code: script, packages });

			// Timeout
			timeout = setTimeout(() => {
				worker.removeEventListener('message', handleMessage);
				worker.removeEventListener('error', handleError);
				try {
					worker.terminate();
				} catch {}
				pyodideWorkerInstance = null;
				reject('Execution Time Limit Exceeded');
			}, 60000);
		});
	};

	export const formatPythonCodeHandler = async () => {
		if (codeEditor) {
			const res = await (
				$user?.role === 'admin'
					? formatPythonCode(localStorage.token, _value)
					: formatPythonCodePyodide(_value)
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
			if (res && res.code) {
				const formattedCode = res.code;
				codeEditor.dispatch({
					changes: [{ from: 0, to: codeEditor.state.doc.length, insert: formattedCode }]
				});

				_value = formattedCode;
				onChange(_value);
				await tick();

				toast.success($i18n.t('Code formatted successfully'));
				return true;
			}
			return false;
		}
		return false;
	};

	let extensions = [
		basicSetup,
		keymap.of([{ key: 'Tab', run: acceptCompletion }, indentWithTab]),
		indentUnit.of('    '),
		placeholder($i18n.t('Enter your code here...')),
		EditorView.updateListener.of((e) => {
			if (e.docChanged) {
				_value = e.state.doc.toString();
				value = _value;
				dispatch('input', _value);
				onChange(_value);
			}
		}),
		editorTheme.of([]),
		editorLanguage.of([]),
		colorSwatchPlugin
	];

	$: if (lang) {
		setLanguage();
	}

	const setLanguage = async () => {
		const language = await getLang();
		if (language && codeEditor) {
			codeEditor.dispatch({
				effects: editorLanguage.reconfigure(language)
			});
		}
	};

	const setTheme = (themeName) => {
		const theme = themeName === 'one-dark' ? oneDark : (themes[themeName] ?? oneDark);
		if (codeEditor) {
			codeEditor.dispatch({
				effects: editorTheme.reconfigure(theme)
			});
		}
	};

	const unsubscribe = codeMirrorTheme.subscribe((theme) => {
		setTheme(theme);
	});

	onMount(() => {
		console.log(value);
		if (value === '') {
			value = boilerplate;
		}

		_value = value;

		// python code editor, highlight python code
		codeEditor = new EditorView({
			state: EditorState.create({
				doc: _value,
				extensions: extensions
			}),
			parent: document.getElementById(`code-textarea-${id}`)
		});

		setTheme($codeMirrorTheme);

		const keydownHandler = async (e) => {
			if ((e.ctrlKey || e.metaKey) && e.key === 's') {
				e.preventDefault();

				onSave();
			}

			// Format code when Ctrl + Shift + F is pressed
			if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'f') {
				e.preventDefault();
				await formatPythonCodeHandler();
			}
		};

		const clickOutsideHandler = (e) => {
			if (ignoreNextClick) {
				ignoreNextClick = false;
				return;
			}
			if (showPicker && !e.target.closest('.color-picker-wrapper')) {
				pickerUpdateCallback(pickerColor);
				showPicker = false;
				activeColorRange = null;
			}
		};

		document.addEventListener('keydown', keydownHandler);
		document.addEventListener('click', clickOutsideHandler);

		return () => {
			document.removeEventListener('keydown', keydownHandler);
			document.removeEventListener('click', clickOutsideHandler);
		};
	});

	onDestroy(() => {
		if (pyodideWorkerInstance) {
			pyodideWorkerInstance.terminate();
		}
		unsubscribe();
	});
</script>

<div id="code-textarea-{id}" class="h-full w-full text-sm" />

{#if showPicker}
	<div class="color-picker-wrapper" style={pickerStyle}>
		<ColorPicker bind:hex={pickerColor} isDialog={false} />
	</div>
{/if}

<style>
	:global(.dark .color-picker-wrapper) {
		--cp-bg-color: #2d2d2d;
		--cp-border-color: #4a4a4a;
		--cp-text-color: #f0f0f0;
		--cp-input-color: #3a3a3a;
		--cp-button-hover-color: #5a5a5a;
	}
</style>
