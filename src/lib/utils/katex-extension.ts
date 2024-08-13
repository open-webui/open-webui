import katex from 'katex'
import 'katex/dist/katex.min.css';
import 'katex/contrib/mhchem';

export default function (options = {}) {
  return {
    extensions: [
      inlineKatex(options),
      blockKatex(options)
    ]
  }
}

function inlineKatex(options) {
  return {
    name: 'inlineKatex',
    level: 'inline',
    start(src: string) {
      return src.indexOf('$')
    },
    tokenizer(src: string) {
      const match = src.match(/^\$+([^$\n]+?)\$+/)
      if (match) {
        return {
          type: 'inlineKatex',
          raw: match[0],
          text: match[1].trim(),
          displayMode: match[0].trim().startsWith('$$')
        }
      }
    },
    renderer(token) {
      return katex.renderToString(token.text, { ...options, displayMode: token.displayMode })
    }
  }
}

function blockKatex(options) {
  return {
    name: 'blockKatex',
    level: 'block',
    start(src: string) {
      return src.indexOf('$$')
    },
    tokenizer(src: string) {
      const match = src.match(/^\$\$+\n([^$]+?)\n\$\$/)
      if (match) {
        return {
          type: 'blockKatex',
          raw: match[0],
          text: match[1].trim(),
          displayMode: match[0].trim().startsWith('$$')
        }
      }
    },
    renderer(token) {
      options.displayMode = true
      return katex.renderToString(token.text, { ...options, displayMode: token.displayMode })
    }
  }
}