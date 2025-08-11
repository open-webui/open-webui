<script lang="ts">
	import { basicSetup, EditorView } from 'codemirror';
	import { keymap, placeholder } from '@codemirror/view';
	import { Compartment, EditorState } from '@codemirror/state';

	import { acceptCompletion } from '@codemirror/autocomplete';
	import { indentWithTab } from '@codemirror/commands';

	import { indentUnit, LanguageDescription } from '@codemirror/language';
	import { languages } from '@codemirror/language-data';

	import { oneDark } from '@codemirror/theme-one-dark';

	import { onMount, createEventDispatcher, getContext, tick, onDestroy } from 'svelte';

	import PyodideWorker from '$lib/workers/pyodide.worker?worker';

	import { formatPythonCode } from '$lib/apis/utils';
	import { toast } from 'svelte-sonner';
	import { user } from '$lib/stores';

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

	onDestroy(() => {
		if (pyodideWorkerInstance) {
			pyodideWorkerInstance.terminate();
		}
	});
</script>

<div id="code-textarea-{id}" class="h-full w-full text-sm" />
