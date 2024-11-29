import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from 'prosemirror-state'

export const AIAutocompletion = Extension.create({
  name: 'aiAutocompletion',

  addOptions() {
    return {
      generateCompletion: () => Promise.resolve(''),
    }
  },

  addGlobalAttributes() {
    return [
      {
        types: ['paragraph'],
        attributes: {
          class: {
            default: null,
            parseHTML: element => element.getAttribute('class'),
            renderHTML: attributes => {
              if (!attributes.class) return {}
              return { class: attributes.class }
            },
          },
          'data-prompt': {
            default: null,
            parseHTML: element => element.getAttribute('data-prompt'),
            renderHTML: attributes => {
              if (!attributes['data-prompt']) return {}
              return { 'data-prompt': attributes['data-prompt'] }
            },
          },
          'data-suggestion': {
            default: null,
            parseHTML: element => element.getAttribute('data-suggestion'),
            renderHTML: attributes => {
              if (!attributes['data-suggestion']) return {}
              return { 'data-suggestion': attributes['data-suggestion'] }
            },
          },
        },
      },
    ]
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('aiAutocompletion'),
        props: {
          handleKeyDown: (view, event) => {
            if (event.key !== 'Tab') return false

            const { state, dispatch } = view
            const { selection } = state
            const { $head } = selection

            if ($head.parent.type.name !== 'paragraph') return false

            const node = $head.parent
            const prompt = node.textContent

            if (!node.attrs['data-suggestion']) {
              // Generate completion
              this.options.generateCompletion(prompt).then(suggestion => {
                if (suggestion && suggestion.trim() !== '') {
                  dispatch(state.tr.setNodeMarkup($head.before(), null, {
                    ...node.attrs,
                    class: 'ai-autocompletion',
                    'data-prompt': prompt,
                    'data-suggestion': suggestion,
                  }))
                }
              })
            } else {
              // Accept suggestion
              const suggestion = node.attrs['data-suggestion']
              dispatch(state.tr
                .insertText(suggestion, $head.pos)
                .setNodeMarkup($head.before(), null, {
                  ...node.attrs,
                  class: null,
                  'data-prompt': null,
                  'data-suggestion': null,
                })
              )
            }

            return true
          },
        },
      }),
    ]
  },
})