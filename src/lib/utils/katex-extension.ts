import katex from 'katex';

const inlineRule = /^(\${1,2})(?!\$)((?:\\.|[^\\\n])*?(?:\\.|[^\\\n\$]))\1(?=[\s?!\.,:？！。，：]|$)/;
const inlineRuleNonStandard = /^(\${1,2})(?!\$)((?:\\.|[^\\\n])*?(?:\\.|[^\\\n\$]))\1/; // Non-standard, even if there are no spaces before and after $ or $$, try to parse

const blockRule = /^(\${1,2})\n((?:\\[^]|[^\\])+?)\n\1(?:\n|$)/;

export default function (options = {}) {
  return {
    extensions: [
      inlineKatex(options, createRenderer(options, false)),
      blockKatex(options, createRenderer(options, true)),
    ],
  };
}

function createRenderer(options, newlineAfter) {
  return (token) => katex.renderToString(token.text, { ...options, displayMode: token.displayMode }) + (newlineAfter ? '\n' : '');
}

function inlineKatex(options, renderer) {
  const nonStandard = options && options.nonStandard;
  const ruleReg = nonStandard ? inlineRuleNonStandard : inlineRule;
  return {
    name: 'inlineKatex',
    level: 'inline',
    // start(src) {
    //   let index;
    //   let indexSrc = src;

    //   while (indexSrc) {
    //     index = indexSrc.indexOf('$');
    //     if (index === -1) {
    //       return;
    //     }
    //     const f = nonStandard ? index > -1 : index === 0 || indexSrc.charAt(index - 1) === ' ';
    //     if (f) {
    //       const possibleKatex = indexSrc.substring(index);

    //       if (possibleKatex.match(ruleReg)) {
    //         return index;
    //       }
    //     }

    //     indexSrc = indexSrc.substring(index + 1).replace(/^\$+/, '');
    //   }
    // },
    tokenizer(src, tokens) {
      const match = src.match(ruleReg);
      if (match) {
        return {
          type: 'inlineKatex',
          raw: match[0],
          text: match[2].trim(),
          displayMode: match[1].length === 2,
        };
      }
    },
    renderer,
  };
}

function blockKatex(options, renderer) {
  return {
    name: 'blockKatex',
    level: 'block',
    tokenizer(src, tokens) {
      const match = src.match(blockRule);
      if (match) {
        return {
          type: 'blockKatex',
          raw: match[0],
          text: match[2].trim(),
          displayMode: match[1].length === 2,
        };
      }
    },
    renderer,
  };
}