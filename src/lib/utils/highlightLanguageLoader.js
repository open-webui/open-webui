import hljs from 'highlight.js/lib/core';

// Pre-load essential languages
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import xml from 'highlight.js/lib/languages/xml'; // for HTML
import css from 'highlight.js/lib/languages/css';
import elixir from 'highlight.js/lib/languages/elixir';

// Custom HCL language definition (since it's not available in highlight.js)
const hclLanguage = {
  keywords: {
    keyword: 'resource data variable locals output module provider terraform required_providers',
    built_in: 'true false null',
    type: 'string number bool list map set object tuple'
  },
  contains: [
    {
      className: 'string',
      begin: '"',
      end: '"',
      contains: [{ className: 'subst', begin: '\\$\\{', end: '\\}' }]
    },
    { className: 'comment', begin: '#', end: '$' },
    { className: 'comment', begin: '/\\*', end: '\\*/' },
    { className: 'number', begin: '\\b\\d+(\\.\\d+)?' }
  ]
};

// Initialize core languages
export const initializeHighlightJS = () => {
  hljs.registerLanguage('javascript', javascript);
  hljs.registerLanguage('typescript', typescript);
  hljs.registerLanguage('python', python);
  hljs.registerLanguage('html', xml);
  hljs.registerLanguage('css', css);
  hljs.registerLanguage('elixir', elixir);
  hljs.registerLanguage('hcl', () => hclLanguage);
  hljs.registerLanguage('terraform', () => hclLanguage);
};

// Dynamic language loading
const languageCache = new Map();

export const loadLanguage = async (lang) => {
  if (hljs.getLanguage(lang)) return true;
  if (languageCache.has(lang)) return languageCache.get(lang);

  try {
    const languageModule = await import(`highlight.js/lib/languages/${lang}`);
    hljs.registerLanguage(lang, languageModule.default);
    languageCache.set(lang, true);
    return true;
  } catch (error) {
    console.warn(`Failed to load language: ${lang}`, error);
    languageCache.set(lang, false);
    return false;
  }
};

// Initialize on import
initializeHighlightJS();

export { hljs };
