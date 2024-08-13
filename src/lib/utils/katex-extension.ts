import katex from 'katex';

// const inlineRule = /^(\${1,2})(?!\$)((?:\\.|[^\\\n])*?(?:\\.|[^\\\n\$]))\1(?=[\s?!\.,:？！。，：]|$)/;
// const inlineRuleNonStandard = /^(\${1,2})(?!\$)((?:\\.|[^\\\n])*?(?:\\.|[^\\\n\$]))\1/; // Non-standard, even if there are no spaces before and after $ or $$, try to parse
const inlineRule = /\$\$([\s\S]*?)\$\$|\$([\s\S]*?)\$/g;
const inlineRuleNonStandard = /\$\$([\s\S]*?)\$\$|\$([\s\S]*?)\$/g;

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
    tokenizer(src) {
      const match = ruleReg.exec(src);
      if (match) {
        console.log('inline match:', match);
        const isBlock = match[0].startsWith('$$');
        const content = isBlock ? match[1] : match[2];
        return {
          type: 'inlineKatex',
          raw: match[0],
          text: content.trim(),
          displayMode: isBlock,
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
    tokenizer(src) {
      const match = src.match(blockRule);
      if (match) {
        console.log('block match:', match);
        return {
          type: 'blockKatex',
          raw: match[0],
          text: match[2].trim(),
          displayMode: true,
        };
      }
    },
    renderer,
  };
}