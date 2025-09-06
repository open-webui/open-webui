import { ViewPlugin, Decoration } from '@codemirror/view';  
import { RangeSetBuilder } from '@codemirror/state';  
import hljs from 'highlight.js';  
  
export const highlightJSExtension = (language) => ViewPlugin.fromClass(  
  class {  
    constructor(view) {  
      this.decorations = this.buildDecorations(view);  
    }  
      
    update(update) {  
      if (update.docChanged) {  
        this.decorations = this.buildDecorations(update.view);  
      }  
    }  
      
    buildDecorations(view) {  
      const builder = new RangeSetBuilder();  
      const code = view.state.doc.toString();  
        
      if (language && hljs.getLanguage(language)) {  
        const result = hljs.highlight(code, { language });  
          
        // Parse highlighted HTML and extract tokens  
        const decorations = [];  
        const tempDiv = document.createElement('div');  
        tempDiv.innerHTML = result.value;  
          
        let pos = 0;  
          
        const walkNodes = (node) => {  
          if (node.nodeType === Node.TEXT_NODE) {  
            pos += node.textContent.length;  
          } else if (node.nodeType === Node.ELEMENT_NODE) {  
            const start = pos;  
              
            // Process children first to get correct end position  
            for (const child of node.childNodes) {  
              walkNodes(child);  
            }  
              
            const end = pos;  
              
            // Add decoration for this element if it has a class  
            if (node.className && start < end) {  
              decorations.push({  
                from: start,  
                to: end,  
                decoration: Decoration.mark({  
                  class: node.className // Use the exact class from highlight.js  
                })  
              });  
            }  
          }  
        };  
          
        for (const child of tempDiv.childNodes) {  
          walkNodes(child);  
        }  
          
        // Sort and add decorations  
        decorations.sort((a, b) => a.from - b.from);  
        for (const dec of decorations) {  
          if (dec.from < dec.to) { // Ensure valid range  
            builder.add(dec.from, dec.to, dec.decoration);  
          }  
        }  
      }  
        
      return builder.finish();  
    }  
  },  
  { decorations: v => v.decorations }  
);
