import { ViewPlugin, Decoration } from '@codemirror/view';
import { RangeSetBuilder } from '@codemirror/state';
import { hljs, loadLanguage } from '$lib/utils/highlightLanguageLoader.js';

export const highlightJSExtension = (language) => ViewPlugin.fromClass(
  class {
    constructor(view) {
      this.view = view;
      this.decorations = this.buildDecorations(view);
      this.loadLanguageIfNeeded(language);
    }

    async loadLanguageIfNeeded(lang) {
      if (lang && !hljs.getLanguage(lang)) {
        const loaded = await loadLanguage(lang);
        if (loaded && this.view) {
          this.decorations = this.buildDecorations(this.view);
        }
      }
    }

    update(update) {
      if (update.docChanged || update.viewportChanged) {
        this.decorations = this.buildDecorations(update.view);
      }
    }

    buildDecorations(view) {
      const builder = new RangeSetBuilder();
      const code = view.state.doc.toString();

      if (language && hljs.getLanguage(language)) {
        const result = hljs.highlight(code, { language });

        const decorations = [];
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = result.value;

        let pos = 0;

        const walkNodes = (node) => {
          if (node.nodeType === Node.TEXT_NODE) {
            pos += node.textContent.length;
          } else if (node.nodeType === Node.ELEMENT_NODE) {
            const start = pos;

            for (const child of node.childNodes) {
              walkNodes(child);
            }

            const end = pos;

            if (node.className && start < end) {
              decorations.push({
                from: start,
                to: end,
                decoration: Decoration.mark({
                  class: node.className
                })
              });
            }
          }
        };

        for (const child of tempDiv.childNodes) {
          walkNodes(child);
        }

        decorations.sort((a, b) => a.from - b.from);
        for (const dec of decorations) {
          if (dec.from < dec.to) {
            builder.add(dec.from, dec.to, dec.decoration);
          }
        }
      }

      return builder.finish();
    }
  },
  { decorations: v => v.decorations }
);
