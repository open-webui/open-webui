import { LanguageDescription } from '@codemirror/language';
import { languages } from '@codemirror/language-data';

const octaveLang = languages.find((l) => l.name === 'Octave');
if (octaveLang) {
	(octaveLang.alias as string[]).push('matlab');
}

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

// Match Computer's Svelte editor: HTML with embedded script and style support.
languages.push(
	LanguageDescription.of({
		name: 'Svelte',
		extensions: ['svelte'],
		load: () => import('@codemirror/lang-html').then((module) => module.html())
	})
);
const shellLanguage = languages.find((language) => language.name === 'Shell');
if (shellLanguage) {
	(shellLanguage.extensions as string[]).push('zsh');
	(shellLanguage.alias as string[]).push('bash', 'zsh');
}
const dockerLanguage = languages.find((language) => language.name === 'Dockerfile');
if (dockerLanguage) {
	(dockerLanguage.extensions as string[]).push('dockerfile');
	languages.push(
		LanguageDescription.of({
			name: 'Containerfile',
			filename: /^(?:Dockerfile|Containerfile)(?:\..+)?$/i,
			load: () => dockerLanguage.load()
		})
	);
}
