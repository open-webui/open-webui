import { marked } from 'marked';

import markedExtension from './extension';
import markedKatexExtension from './katex-extension';
import { disableSingleTilde } from './strikethrough-extension';
import { mentionExtension } from './mention-extension';
import footnoteExtension from './footnote-extension';
import citationExtension from './citation-extension';

const options = {
	throwOnError: false,
	breaks: true
};

marked.use(markedKatexExtension(options));
marked.use(markedExtension(options));
marked.use(citationExtension());
marked.use(footnoteExtension());
marked.use(disableSingleTilde);
marked.use({
	extensions: [
		mentionExtension({ triggerChar: '@' }),
		mentionExtension({ triggerChar: '#' }),
		mentionExtension({ triggerChar: '$' })
	]
});

export { marked };
