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
