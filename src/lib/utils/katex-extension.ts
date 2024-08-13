import katex from 'katex'
import 'katex/dist/katex.css'
import marked from 'marked'

export default function (options): marked.MarkedExtension {
  options.throwOnError = false
  return {
    extensions: [
      inlineKatex(options),
      blockKatex(options)
    ]
  }
}

function inlineKatex(options): marked.TokenizerAndRendererExtension {
  return {
    name: 'inlineKatex',
    level: 'inline',
    start(src: string) {
      return src.indexOf('$')
    },
    tokenizer(src: string, _tokens) {
      const match = src.match(/^\$+([^$\n]+?)\$+/)
      if (match) {
        return {
          type: 'inlineKatex',
          raw: match[0],
          text: match[1].trim()
        }
      }
    },
    renderer(token) {
      return katex.renderToString(token.text, options)
    }
  }
}

function blockKatex(options): marked.TokenizerAndRendererExtension {
  return {
    name: 'blockKatex',
    level: 'block',
    start(src: string) {
      return src.indexOf('$$')
    },
    tokenizer(src: string, _tokens) {
      const match = src.match(/^\$\$+\n([^$]+?)\n\$\$/)
      if (match) {
        return {
          type: 'blockKatex',
          raw: match[0],
          text: match[1].trim()
        }
      }
    },
    renderer(token) {
      options.displayMode = true
      return `<p>${katex.renderToString(token.text, options)}</p>`
    }
  }
}