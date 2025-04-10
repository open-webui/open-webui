<script lang="ts">
	import { basicSetup, EditorView } from 'codemirror';
	import { keymap, placeholder } from '@codemirror/view';
	import { Compartment, EditorState } from '@codemirror/state';

	import { acceptCompletion } from '@codemirror/autocomplete';
	import { indentWithTab } from '@codemirror/commands';

	import { indentUnit, LanguageDescription } from '@codemirror/language';
	import { languages } from '@codemirror/language-data';

	import { oneDark } from '@codemirror/theme-one-dark';

	import { onMount, createEventDispatcher, getContext, tick } from 'svelte';

	import { formatPythonCode } from '$lib/apis/utils';
	import { toast } from 'svelte-sonner';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let boilerplate = '';
	export let value = '';

	export let onSave = () => {};
	export let onChange = () => {};

	let _value = '';

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
	function findChanges(oldStr, newStr) {
		let changes = [];
		let oldIndex = 0,
			newIndex = 0;

		while (oldIndex < oldStr.length || newIndex < newStr.length) {
			if (oldStr[oldIndex] !== newStr[newIndex]) {
				let start = oldIndex;

				// Identify the changed portion
				while (oldIndex < oldStr.length && oldStr[oldIndex] !== newStr[newIndex]) {
					oldIndex++;
				}
				while (newIndex < newStr.length && newStr[newIndex] !== oldStr[start]) {
					newIndex++;
				}

				changes.push({
					from: start,
					to: oldIndex, // Replace the differing part
					insert: newStr.substring(start, newIndex)
				});
			} else {
				oldIndex++;
				newIndex++;
			}
		}

		return changes;
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

	export const formatPythonCodeHandler = async () => {
		if (codeEditor) {
			const res = await formatPythonCode(localStorage.token, _value).catch((error) => {
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
		placeholder('Enter your code here...'),
		EditorView.updateListener.of((e) => {
			if (e.docChanged) {
				_value = e.state.doc.toString();
				onChange(_value);
			}
		}),
		editorTheme.of([]),
		editorLanguage.of([])
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

	onMount(() => {
		console.log(value);
		if (value === '') {
			value = boilerplate;
		}

		_value = value;

		// Check if html class has dark mode
		isDarkMode = document.documentElement.classList.contains('dark');

		// python code editor, highlight python code
		codeEditor = new EditorView({
			state: EditorState.create({
				doc: _value,
				extensions: extensions
			}),
			parent: document.getElementById(`code-textarea-${id}`)
		});

		if (isDarkMode) {
			codeEditor.dispatch({
				effects: editorTheme.reconfigure(oneDark)
			});
		}

		// listen to html class changes this should fire only when dark mode is toggled
		const observer = new MutationObserver((mutations) => {
			mutations.forEach((mutation) => {
				if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
					const _isDarkMode = document.documentElement.classList.contains('dark');

					if (_isDarkMode !== isDarkMode) {
						isDarkMode = _isDarkMode;
						if (_isDarkMode) {
							codeEditor.dispatch({
								effects: editorTheme.reconfigure(oneDark)
							});
						} else {
							codeEditor.dispatch({
								effects: editorTheme.reconfigure()
							});
						}
					}
				}
			});
		});

		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class']
		});

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

		document.addEventListener('keydown', keydownHandler);

		return () => {
			observer.disconnect();
			document.removeEventListener('keydown', keydownHandler);
		};
	});
</script>

<div id="code-textarea-{id}" class="h-full w-full text-sm" />
