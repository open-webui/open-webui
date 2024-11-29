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
            const { state, dispatch } = view
            const { selection } = state
            const { $head } = selection

            if ($head.parent.type.name !== 'paragraph') return false

            const node = $head.parent

            if (event.key === 'Tab') {
              if (!node.attrs['data-suggestion']) {
                // Generate completion
                const prompt = node.textContent
                this.options.generateCompletion(prompt).then(suggestion => {
                  if (suggestion && suggestion.trim() !== '') {
                    dispatch(state.tr.setNodeMarkup($head.before(), null, {
                      ...node.attrs,
                      class: 'ai-autocompletion',
                      'data-prompt': prompt,
                      'data-suggestion': suggestion,
                    }))
                  }
                  // If suggestion is empty or null, do nothing
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
            } else if (node.attrs['data-suggestion']) {
              // Reset suggestion on any other key press
              dispatch(state.tr.setNodeMarkup($head.before(), null, {
                ...node.attrs,
                class: null,
                'data-prompt': null,
                'data-suggestion': null,
              }))
            }

            return false
          },
        },
      }),
    ]
  },
})