<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { chatId, showArtifacts, showControls, hideInline, codeBlockTitles } from '$lib/stores';
	import XMark from '../icons/XMark.svelte';
	import { copyToClipboard, createMessagesList } from '$lib/utils';
	import ArrowsPointingOut from '../icons/ArrowsPointingOut.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import SvgPanZoom from '../common/SVGPanZoom.svelte';
	import ArrowLeft from '../icons/ArrowLeft.svelte';
	import { cat } from '@huggingface/transformers';
	import Search from '../icons/Search.svelte';

	export let overlay = false;
	export let viewMode: 'Design' | 'Design' = 'Code';
    export let showDiffs = true;
	export let history;
	let messages = [];

	let contents: Array<{ type: string; content: string }> = [];
	let selectedContentIdx = 0;
    let codeSliderIndex = 0;

    
	let copied = false;
	let iframeElement: HTMLIFrameElement;

	$: if (history) {
		messages = createMessagesList(history, history.currentId);
		getContents();
	} else {
		messages = [];
		getContents();
	}

    window.addEventListener('message', function(event) {
                    if (event.data.type === 'FROM_IFRAME') {
                        codeSliderIndex = event.data.data as number;
                    }
                    if (event.data.type === 'FROM_MDT') {
                        //moveIframeCarousel(index);
                    }
            });


    function getComponentNameFromCode(code) {
        // Try to find the default export
        const defaultExportRegex = /export\s+default\s+(\w+);/;
        let match = code.match(defaultExportRegex);
        if (match && match[1]) {
            return match[1];
        }

        // If no default export is found, try to find the first function declaration
        const functionDeclarationRegex = /function\s+(\w+)\s*\(/;
        match = code.match(functionDeclarationRegex);
        if (match && match[1]) {
            return match[1];
        }

        // If no function declaration is found, try to find the first arrow function expression
        const arrowFunctionRegex = /const\s+(\w+)\s*=\s*\(.*?\)\s*=>/;
        match = code.match(arrowFunctionRegex);
        if (match && match[1]) {
            return match[1];
        }

        // If no function is found, throw an error
        throw new Error('No default export or function found in the code');
    }

    function cleanReactImports(code) {
        if (typeof code !== 'string') {
            throw new TypeError('Expected a string for the code parameter');
        }

        // Remove all import statements
        code = code.replace(/import\s+.*?['"].*?['"];?/g, '');

        // Escape backticks and `${`
        code = code.replace(/`/g, '\\`').replace(/\$\{/g, '\\${');

        // Remove export statements
        code = code.replace(/^\s*export\s.*$/gm, '');

        return code;
    }

    function moveIframeCarousel(index: number) {
        if (iframeElement?.contentWindow) {
            // Check if the iframe is mounted and has a contentWindow
            if (typeof index === 'number') {
                iframeElement.contentWindow.postMessage(
                    { type: 'MOVE_CAROUSEL', data: index },
                    '*'
                );
            }
        }
    }

    function getHistoryParent(history: { messages: { [key: string]: any } }, key: string, passthru: string): string | null {
        const messages = history.messages;
        const current = messages[key];

        if (current.role === 'assistant' && current.id !== passthru) {
            return current.id;
        }

        if (!current.parentId) {
            return null;
        }

        return getHistoryParent(history, current.parentId, passthru);
        }

	const getContents = (keepSelectedContent: boolean = false) => {
    contents = [];

    messages.forEach((message) => {
        let codeBlockMap = {};
        if (message?.role !== 'user' && message?.content) {
            let compareparent = getHistoryParent(history, message.id, message.id);


            function extractTitle(line, fallbackLines = []) {
                // Try to extract title from the primary line
                const match = line.match(/^#{1,7} (.*)$/);
                if (match) {
                    return match[1].trim().replace(/`/g, '');
                }
                
                // If no title found in the primary line, try each fallback line
                for (const fallbackLine of fallbackLines) {
                    const fallbackMatch = fallbackLine.match(/^#{1,7} (.*)$/);
                    if (fallbackMatch) {
                        return fallbackMatch[1].trim().replace(/`/g, '');
                    }
                }
                
                // Return null or some default value if no title is found in any line
                return null;
            }
            // Function to calculate the similarity ratio between two code blocks
            function calculateSimilarity(code1, code2) {
                const lines1 = code1.split('\n');
                const lines2 = code2.split('\n');
                const commonLines = lines1.filter(line => lines2.includes(line));
                const similarityRatio = commonLines.length / Math.max(lines1.length, lines2.length);
                
                // Check if code1 has a corresponding title in codeBlockTitleMap
                // and if that title matches the corresponding title in oldCodeBlockTitleMap for code2
                const code1Title = codeBlockTitles[code1.trim()];
                const code2OldTitle = codeBlockTitles[code2.trim()];
                if (code1Title && code2OldTitle && code1Title === code2OldTitle) {
                    // Add 0.2 to the similarity ratio if the titles match
                    return Math.min(similarityRatio + 0.2, 1); // Ensure the ratio doesn't exceed 1
                }
                
                return similarityRatio;
            }

            // Parse code blocks from the current message
            const codeBlockContents = message.content.match(/```[\s\S]*?```/g);
            let codeBlocks = [];
            if (codeBlockContents) {
                const lines = message.content.split('\n');
    codeBlockContents.forEach((block) => {
        const lang = block.split('\n')[0].replace('```', '').trim().toLowerCase();
        const code = block.replace(/```[\s\S]*?\n/, '').replace(/```$/, '');
        codeBlocks.push({ lang, code });
        // Find the index of the code block in the message content
        const blockStartIndex = message.content.indexOf(block);
        // Find the index of the line where the code block starts
        let blockStartLineIndex = 0;
        let currentIndex = 0;
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (currentIndex <= blockStartIndex && blockStartIndex < currentIndex + line.length) {
                blockStartLineIndex = i;
                break;
            }
            currentIndex += line.length + 1; // +1 for newline character
        }
        // Extract title from previous line
        const title = extractTitle(
        lines[blockStartLineIndex - 1],
        lines.slice(Math.max(0, blockStartLineIndex - 6), blockStartLineIndex - 1).reverse()
    );

    if (title) {
        codeBlockTitles[code.trim()] = title;
        //console.log(title);
    }
});
                codeBlockContents.forEach((block, index) => {
                const lang = block.split('\n')[0].replace('```', '').trim().toLowerCase();
                const code = block.replace(/```[\s\S]*?\n/, '').replace(/```$/, '');
                codeBlocks.push({ lang, code });

                });
            }


            // If compareparent exists, parse its code blocks and map similar blocks
            if (compareparent && history.messages[compareparent]) {
                let parentObj = history.messages[compareparent]

                const oldCodeBlockContents = parentObj.content.match(/```[\s\S]*?```/g);
                let oldCodeBlocks = [];
                if (oldCodeBlockContents) {
                    oldCodeBlockContents.forEach((block, index) => {
                        const lang = block.split('\n')[0].replace('```', '').trim().toLowerCase();
                        const code = block.replace(/```[\s\S]*?\n/, '').replace(/```$/, '');
                        oldCodeBlocks.push({ lang, code });
                        const title = extractTitle(
    parentObj.content.split('\n')[index],
    parentObj.content.split('\n').slice(Math.max(0, index - 6), index).reverse()
);
                        if (title) {
                            codeBlockTitles[code.trim()] = title;
                        }
                    });
                }

                // Create a dictionary to map current code blocks to their old versions
                codeBlocks.forEach((currentBlock) => {
                    let maxSimilarity = 0;
                    let bestMatch = null;

                    oldCodeBlocks.forEach((oldBlock) => {
                        if (currentBlock.lang === oldBlock.lang) {
                            const similarity = calculateSimilarity(currentBlock.code, oldBlock.code);
                            if (similarity > maxSimilarity) {
                                maxSimilarity = similarity;
                                bestMatch = oldBlock.code;
                            }
                        }
                    });

                    if (maxSimilarity >= 0.5) {
                        codeBlockMap[currentBlock.code] = bestMatch;
                    }
                });


            }

            const allowedLanguages = new Set([
  'html', 'css', 'javascript', 'js', 'typescript', 'ts', 'csharp', 'python', 'java',
  'php', 'ruby', 'bash', 'shell', 'applescript', 'sql', 'json', 'xml', 'xaml', 'yaml', 'markdown',
  'c', 'c++', 'powershell', 'sh', 'scheme', 'dart', 'liquid', 'asp', 'kotlin', 'jsx', 'react'
]);

            const codeDictionary = {};

            codeBlocks.forEach((block) => {
                const { lang, code } = block;
                if (allowedLanguages.has(lang)) {
                    if (!codeDictionary[lang]) {
                        codeDictionary[lang] = [];
                    }
                    if (!codeDictionary[lang].includes(code)) {
                        codeDictionary[lang].push(code);
                    }
                } else {
                    console.warn(`Language "${lang}" is not allowed and will be ignored.`);
                }
            });

            const inlineHtml = message.content.match(/<html>[\s\S]*?<\/html>/gi);
            const inlineCss = message.content.match(/<style>[\s\S]*?<\/style>/gi);
            const inlineJs = message.content.match(/<script>[\s\S]*?<\/script>/gi);
            if (inlineHtml) {
                inlineHtml.forEach((block) => {
                    const content = block.replace(/<\/?html>/gi, ''); // Remove <html> tags
                    if (!codeDictionary.html) {
                        codeDictionary.html = [];
                    }
                    codeDictionary.html.push(content.trim());
                });
            }

            if (inlineCss) {
                inlineCss.forEach((block) => {
                    const content = block.replace(/<\/?style>/gi, ''); // Remove <style> tags
                    if (!codeDictionary.css) {
                        codeDictionary.css = [];
                    }
                    codeDictionary.css.push(content.trim());
                });
            }

            if (inlineJs) {
                inlineJs.forEach((block) => {
                    const content = block.replace(/<\/?script>/gi, ''); // Remove <script> tags
                    if (!codeDictionary.javascript) {
                        codeDictionary.javascript = [];
                    }
                    codeDictionary.javascript.push(content.trim());
                });
            }

            if (codeDictionary.javascript && codeDictionary.js) {
                codeDictionary.javascript = codeDictionary.javascript.concat(codeDictionary.js);
                delete codeDictionary.js;
            }

            if (codeDictionary.react && codeDictionary.jsx) {
                codeDictionary.react = codeDictionary.react.concat(codeDictionary.jsx);
                delete codeDictionary.jsx;
            }
            else if (codeDictionary.jsx && !codeDictionary.react){
                codeDictionary.react = codeDictionary.jsx;
                delete codeDictionary.jsx;
            }

            if (
                (codeDictionary.html || codeDictionary.css || codeDictionary.javascript || codeDictionary.react) && viewMode === 'Design'
            ) {
                let renderedContent = ``;
                if (codeDictionary.react){
                    renderedContent = `
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>React Renderer</title>
                    <${''}script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></${''}script>
                    <${''}script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></${''}script>
                    <${''}script src="https://unpkg.com/@babel/standalone/babel.min.js"></${''}script>
                    <${''}script src="https://cdn.tailwindcss.com"></${''}script>
                        <${''}style>
                            body {
                                background-color: white;
                                background-image: 
                                    linear-gradient(45deg, #e0e0e0 25%, transparent 25%),
                                    linear-gradient(45deg, transparent 75%, #e0e0e0 75%),
                                    linear-gradient(45deg, #e0e0e0 25%, transparent 25%),
                                    linear-gradient(45deg, transparent 75%, #e0e0e0 75%);
                                background-position: 
                                    0 0, 
                                    0 0, 
                                    15px 15px, 
                                    15px 15px;
                                background-size: 30px 30px;
                                min-height: 100vh;
                            }
                            ${(codeDictionary.css || []).join('\n').replace("body",".renderer-body")}
                        </${''}style>
                    </head>
                    <body style="display:block; height:100vh; width:100%">
                    <div class="bg-gray-950" style="width:100%; style="height: 3rem">
                        <div class="flex items-center justify-center text-white text-sm" style="height: 3rem">
                            <div class="flex items-center justify-between text-white text-sm pt-3 mb-3">
                                <div class="flex items-center">
                                    <button class="bg-gray-700 text-white w-8 h-8 rounded-full z-10 hover:bg-gray-600 transition-colors" onclick="moveCarousel(-1)">
                                    <span class="text-xl">‹</span>
                                    </button>
                                    <div class="font-semibold mx-2">Code</div>
                                    <button class="bg-gray-700 text-white w-8 h-8 rounded-full z-10 hover:bg-gray-600 transition-colors" onclick="moveCarousel(1)">
                                    <span class="text-xl">›</span>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                            <div class="relative w-full">
            <div class="overflow-hidden relative">
                    <div class="flex space-x-0 transition-transform duration-500" id="carousel">
                    ${codeDictionary.react.map((block, blockIndex) => {
                        const fileName = codeBlockTitles[block.trim()] || '';;
                        return `
                                    <div class="reactchild flex-shrink-0 w-full">
                                        <div class="bg-gray-800 rounded-lg shadow-lg" style="height: calc(100vh - 3rem)">
                                            <div class="renderer-body" style="height: calc(100vh - 3rem) !important" id="root-${blockIndex}" data-filename="${fileName}"></div>
                                        </div>
                                    </div>
                                `;
                    }).join('')
                    
                        }

                    
                    </div>
                    </div>
                    </div>
                    <${''}script>
                        function getSelectedCode(displayName) {
                                const lang = displayName.toLowerCase();
                                return lang;
                            }

                        // Function to move the carousel
                        let currentIndex = ${codeSliderIndex};
                        const items = document.querySelectorAll('#carousel .reactchild');
                        const reactchildren = document.querySelectorAll('.reactchild');
                        const totalItems = items.length;
                            
                        function moveCarousel(direction) {
                            //console.log(items);
                            //console.log(totalItems);
                            //console.log(reactchildren);
                            // Get the width of each item including margin/padding
                            const item = items[0];
                            const style = getComputedStyle(item);
                            const itemWidth = item.offsetWidth + parseInt(style.marginLeft) + parseInt(style.marginRight);
                            // Update the current index based on direction
                            currentIndex += direction;
                            // Loop back to the first item or last item
                            if (currentIndex < 0) currentIndex = totalItems - 1;
                            if (currentIndex >= totalItems) currentIndex = 0;
                            window.parent.postMessage({ type: 'FROM_IFRAME', data: currentIndex }, '*');
                            // Calculate the new offset considering margin
                            const offset = -currentIndex * itemWidth;
                            // Apply the new transform to the carousel container
                            document.querySelector('#carousel').style.transform = 'translateX(' + offset + 'px)';
                            const fileName = reactchildren[currentIndex].querySelector('.renderer-body').dataset.filename;
                            document.querySelector('.font-semibold.mx-2').textContent = fileName ?? currentIndex;
                        }

                        function renderReact() {
                        
                        ${codeDictionary.react.map((block, blockIndex) => {
                            //console.log(block)
                            try{
                                return `
                                    try{
                                        const code = \`${cleanReactImports(codeDictionary.react[blockIndex])}\`;
                                        const transpiledCode = Babel.transform(code, { presets: ['react'] }).code;
                                        
                                        // Create a new function scope and evaluate the code
                                        const wrapper = new Function('React', 'const { useState, useEffect, useContext, useReducer, useRef, useMemo, useCallback, useLayoutEffect, useImperativeHandle, useDeferredValue, useId, useSyncExternalStore, useTransition, useDebugValue, useCacheQueryData } = React;\\n' + transpiledCode + '\\nreturn ${getComponentNameFromCode(codeDictionary.react[blockIndex])};');
                                        
                                        // Execute the wrapper function with React as parameter
                                        const Component = wrapper(React);
                                        
                                        const root = ReactDOM.createRoot(document.getElementById('root-${blockIndex}'));
                                        root.render(React.createElement(Component));
                                    }
                                    catch {
                                        console.log("Error rendering: " + error)
                                    }
                                `;
                            }
                            catch{
                                return '';
                            }
                        }
                            ).join('\n')}
                    
                        }

                        renderReact();
                        const fileName = reactchildren[${codeSliderIndex}].querySelector('.renderer-body').dataset.filename;
                        document.querySelector('.font-semibold.mx-2').textContent = fileName ?? ${codeSliderIndex};
                    </${''}script>
                    </body>
                    </html>
                `;
                }
                else{
                    renderedContent = `
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <${''}script src="https://cdn.tailwindcss.com"></${''}script>
                        <${''}style>
                            body {
                                background-color: white; /* Ensure the iframe has a white background */
                            }
                            ${(codeDictionary.css || []).join('\n').replace("body",".renderer-body")}
                        </${''}style>
                    </head>
                    <body>
                    <div class="renderer-body" style="height: calc(100vh - 3rem) !important">
                        ${(codeDictionary.html || []).join('\n')}
                        </div>
                        <${''}script>
                            ${(codeDictionary.javascript || []).join('\n')}
                        </${''}script>
                    </body>
                    </html>
                `;
                }
                

                contents = [...contents, { type: 'iframe', content: renderedContent }];
            } else if ((
                codeDictionary.csharp ||
  codeDictionary.python ||
  codeDictionary.java ||
  codeDictionary.php ||
  codeDictionary.ruby ||
  codeDictionary.bash ||
  codeDictionary.sh ||
  codeDictionary.shell ||
  codeDictionary.applescript ||
  codeDictionary.sql ||
  codeDictionary.json ||
  codeDictionary.xml ||
  codeDictionary.yaml ||
  codeDictionary.markdown ||
  codeDictionary.html ||
  codeDictionary.css ||
  codeDictionary.javascript ||
  codeDictionary.js ||
  codeDictionary.typescript ||
  codeDictionary.ts ||
  codeDictionary.c ||
  codeDictionary.jsx ||
  codeDictionary['c++'] ||
  codeDictionary.powershell ||
  codeDictionary.scheme ||
  codeDictionary.dart ||
  codeDictionary.liquid ||
  codeDictionary.react ||
  codeDictionary.asp ||
  codeDictionary.kotlin) && viewMode === 'Code') {
                    const codeMirrorModes = {
                    html: 'text/html',
                    css: 'css',
                    javascript: 'javascript',
                    js: 'javascript',
                    typescript: 'application/typescript',
                    ts: 'application/typescript',
                    csharp: 'text/x-csharp',
                    python: 'python',
                    java: 'text/x-java',
                    php: 'application/x-httpd-php',
                    ruby: 'ruby',
                    bash: 'shell',
                    shell: 'shell',
                    sh: 'shell',
                    applescript: 'applescript',
                    sql: 'sql',
                    json: 'application/json',
                    xml: 'xml',
                    xaml: 'xaml',
                    yaml: 'text/yaml',
                    markdown: 'markdown',
                    c: 'text/x-csrc',
                    'c++': 'text/x-c++src',
                    powershell: 'powershell',
                    scheme: 'scheme',
                    dart: 'dart',
                    liquid: 'text/x-liquid',
                    asp: 'aspnet',
                    kotlin: 'text/x-kotlin',
                    };
                let htmlContent = '';


                const renderedContent = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <${''}script src="https://cdn.tailwindcss.com"></${''}script>
    <${''}script src="https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs/loader.js"></${''}script>
    <link href="https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs/editor/editor.main.min.css" rel="stylesheet">
    <${''}style>
        body { background-color: white; }
        .editor-instance { 
            min-height: 200px;  
            width: 100%;
            margin-bottom: 1rem; 
        }
        .diff-mode { 
            display: flex; 
            width: 100%; 
            height: calc(100vh - 3rem); 
        }

    </${''}style>
</head>
<body class="bg-gray-50 dark:bg-gray-950" style="height:100vh; width:100%">
    <div class="flex items-center justify-center text-white text-sm" style="height: 3rem">
        <div class="flex items-center justify-between text-white text-sm pt-3 mb-3">
            <div class="flex items-center">
                <button class="bg-gray-700 text-white w-8 h-8 rounded-full z-10 hover:bg-gray-600 transition-colors" onclick="moveCarousel(-1)">
                <span class="text-xl">‹</span>
                </button>
                <div class="font-semibold mx-2">Code</div>
                <button class="bg-gray-700 text-white w-8 h-8 rounded-full z-10 hover:bg-gray-600 transition-colors" onclick="moveCarousel(1)">
                <span class="text-xl">›</span>
                </button>
            </div>
        </div>
    </div>
    <div id="editor-container" class="w-full">
        <div class="relative w-full">
            <div class="overflow-hidden relative">
                <div class="flex space-x-0 transition-transform duration-500" id="carousel">
                    ${Object.entries(codeDictionary)
                        .filter(([lang]) => allowedLanguages.has(lang))
                        .map(([lang, blocks], langIndex) =>
                            blocks.map((block, blockIndex) => {
                                const editorId = `${lang}Editor-${blockIndex}`;
                                const displayName = lang.charAt(0).toUpperCase() + lang.slice(1);
                                const fileName = codeBlockTitles[block.trim()] || '';;
                                const originalCode = codeBlockMap[block] || '';
                                return `
                                    <div class="flex-shrink-0 w-full">
                                        <div class="bg-gray-800 rounded-lg shadow-lg" style="height: calc(100vh - 3rem)">
                                            <div class="flex h-full">
                                                <div id="${editorId}" 
                                                     class="editor-instance w-full" 
                                                     style="height: 100%" 
                                                     data-code="${encodeURIComponent(block)}" 
                                                     data-original-code="${encodeURIComponent(originalCode)}" 
                                                     data-language="${lang}"
                                                     data-filename="${fileName}">
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                `;
                            }).join('')
                        ).join('')
                    }
                </div>
            </div>
        </div>
    </div>

    <${''}script>
        window.addEventListener('message', function(event) {
            if (event.data.type === 'MOVE_CAROUSEL') {
                _moveCarouselToSpecificIndex(event.data.data);
            }
        });
        function getSelectedCode(displayName) {
            const lang = displayName.toLowerCase();
            return lang;
        }

        // Function to move the carousel
        let currentIndex = ${codeSliderIndex};
        const items = document.querySelectorAll('#carousel .flex-shrink-0');
        const totalItems = items.length;
            

        function _moveCarouselToSpecificIndex(index) {
            // Get the carousel items
            const items = document.querySelectorAll('#carousel .flex-shrink-0');
            const totalItems = items.length;
            
            // Ensure the index is within valid range
            if (index < 0) index = 0;
            if (index >= totalItems) index = totalItems - 1;
            
            // Calculate the offset based on the index
            const item = items[0];
            const style = getComputedStyle(item);
            const itemWidth = item.offsetWidth + parseInt(style.marginLeft) + parseInt(style.marginRight);
            const offset = -index * itemWidth;
            
            // Update the current index
            currentIndex = index;
            
            // Apply the new transform to the carousel container
            document.querySelector('#carousel').style.transform = 'translateX(' + offset + 'px)';
            
            // Notify the parent
            window.parent.postMessage({ type: 'FROM_IFRAME', data: currentIndex }, '*');
        }

        
        function moveCarousel(direction) {
            // Get the width of each item including margin/padding
            const item = items[0];
            const style = getComputedStyle(item);
            const itemWidth = item.offsetWidth + parseInt(style.marginLeft) + parseInt(style.marginRight);
            // Update the current index based on direction
            currentIndex += direction;
            // Loop back to the first item or last item
            if (currentIndex < 0) currentIndex = totalItems - 1;
            if (currentIndex >= totalItems) currentIndex = 0;
            window.parent.postMessage({ type: 'FROM_IFRAME', data: currentIndex }, '*');
            // Calculate the new offset considering margin
            const offset = -currentIndex * itemWidth;
            // Apply the new transform to the carousel container
            document.querySelector('#carousel').style.transform = 'translateX(' + offset + 'px)';
            // Update the selected code
            const selectedLanguage = items[currentIndex].querySelector('.editor-instance').dataset.language;
            const fileName = items[currentIndex].querySelector('.editor-instance').dataset.filename;
            let selectedDisplayName = selectedLanguage.charAt(0).toUpperCase() + selectedLanguage.slice(1);
            if (selectedDisplayName == 'Csharp'){
                selectedDisplayName = 'C#';
            }

            let displayText = '';
            if (fileName){
                displayText = fileName + ' (' + selectedDisplayName + ')';
            }
            else{
                displayText = selectedDisplayName;
            }

            document.querySelector('.font-semibold.mx-2').textContent = displayText
        }
        document.addEventListener('DOMContentLoaded', function () {
            const editorInstances = document.querySelectorAll('.editor-instance');
            
            require.config({
                paths: {
                    vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs'
                }
            });

            require(['vs/editor/editor.main'], function () {
                editorInstances.forEach((container) => {
                    const code = decodeURIComponent(container.dataset.code);
                    const originalCode = decodeURIComponent(container.dataset.originalCode);
                    const lang = container.dataset.language;
                    
                    const modeMap = {
                        'csharp': 'csharp',
                        'javascript': 'javascript',
                        'html': 'html',
                        'css': 'css',
                        'python': 'python',
                        // ... other language mappings
                    };

                    // Create diff editor if original code exists
                    if (originalCode && ${showDiffs}) {
    const diffEditor = monaco.editor.createDiffEditor(container, {
        theme: 'vs-dark',
        automaticLayout: true,
        renderSideBySide: true, // Keep it as a single column for more compact viewing
        fontSize: 12,
        lineHeight: 16,
        scrollBeyondLastLine: false
    });

    const originalModel = monaco.editor.createModel(originalCode, modeMap[lang] || 'javascript');
    const modifiedModel = monaco.editor.createModel(code, modeMap[lang] || 'javascript');

    diffEditor.setModel({
        original: originalModel,
        modified: modifiedModel
    });

    // Optional: Adjust diff rendering for improved compactness
    diffEditor.updateOptions({
        ignoreTrimWhitespace: true
    });
} else {
    // Create standard editor if no original code
    const editor = monaco.editor.create(container, {
        value: code,
        language: modeMap[lang] || 'javascript',
        theme: 'vs-dark',
        automaticLayout: true,
        fontSize: 12,
        lineHeight: 16,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: 'on'
    });
}
                });
            });
        });
        const selectedLanguage = items[currentIndex].querySelector('.editor-instance').dataset.language;
    let selectedDisplayName = selectedLanguage.charAt(0).toUpperCase() + selectedLanguage.slice(1);
    let fileName = items[currentIndex].querySelector('.editor-instance').dataset.filename;
    if (selectedDisplayName == 'Csharp'){
        selectedDisplayName = 'C#';
    }
    let displayText = '';
    if (fileName){
        displayText = fileName + ' (' + selectedDisplayName + ')';
    }
    else{
        displayText = selectedDisplayName;
    }

    document.querySelector('.font-semibold.mx-2').textContent = displayText
    </${''}script>
</body>
</html>
`;



                contents = [...contents, { type: 'iframe', content: renderedContent }];
            } else {
                // Check for SVG content
                for (const block of codeBlocks) {
                    if (block.lang === 'svg' || (block.lang === 'xml' && block.code.includes('<svg'))) {
                        contents = [...contents, { type: 'svg', content: block.code }];
                    }
                }
            }
			if (contents.length === 0) {
                if ((
                    codeDictionary.csharp ||
                    codeDictionary.python ||
                    codeDictionary.java ||
                    codeDictionary.php ||
                    codeDictionary.ruby ||
                    codeDictionary.bash ||
                    codeDictionary.shell ||
                    codeDictionary.sh ||
                    codeDictionary.applescript ||
                    codeDictionary.sql ||
                    codeDictionary.json ||
                    codeDictionary.xml ||
                    codeDictionary.yaml ||
                    codeDictionary.markdown ||
                    codeDictionary.html ||
                    codeDictionary.css ||
                    codeDictionary.javascript ||
                    codeDictionary.js ||
                    codeDictionary.typescript ||
                    codeDictionary.ts ||
                    codeDictionary.jsx ||
                    codeDictionary.react ||
                    codeDictionary.c ||
                    codeDictionary['c++'] ||
                    codeDictionary.powershell ||
                    codeDictionary.sh ||
                    codeDictionary.scheme ||
                    codeDictionary.dart ||
                    codeDictionary.liquid ||
                    codeDictionary.asp ||
                    codeDictionary.kotlin) && viewMode === 'Design')
                {
                    viewMode = 'Code';
                    getContents(true);
                }
				if ((
                    codeDictionary.html ||
                    codeDictionary.css ||
                    codeDictionary.javascript) && viewMode === 'Code')
				{
					viewMode = 'Design';
					getContents(true);
				}
			}
        }
    });

    if (!keepSelectedContent){
        selectedContentIdx = contents ? contents.length - 1 : 0;
    }

};

	function navigateContent(direction: 'prev' | 'next') {


		selectedContentIdx =
			direction === 'prev'
				? Math.max(selectedContentIdx - 1, 0)
				: Math.min(selectedContentIdx + 1, contents.length - 1);


	}

	const iframeLoadHandler = () => {

		iframeElement.contentWindow.addEventListener(
			'click',
			function (e) {
				const target = e.target.closest('a');
				if (target && target.href) {
					e.preventDefault();
					const url = new URL(target.href, iframeElement.baseURI);
					if (url.origin === window.location.origin) {
						iframeElement.contentWindow.history.pushState(
							null,
							'',
							url.pathname + url.search + url.hash
						);
					} else {

					}
				}
			},
			true
		);

		// Cancel drag when hovering over iframe
		iframeElement.contentWindow.addEventListener('mouseenter', function (e) {
			e.preventDefault();
			iframeElement.contentWindow.addEventListener('dragstart', (event) => {
				event.preventDefault();
			});
		});
	};

	const showFullScreen = () => {
		if (iframeElement.requestFullscreen) {
			iframeElement.requestFullscreen();
		} else if (iframeElement.webkitRequestFullscreen) {
			iframeElement.webkitRequestFullscreen();
		} else if (iframeElement.msRequestFullscreen) {
			iframeElement.msRequestFullscreen();
		}
	};

	onMount(() => {});
</script>

<div class=" w-full h-full relative flex flex-col bg-gray-50 dark:bg-gray-850">
	<div class="w-full h-full flex-1 relative">
		{#if overlay}
			<div class=" absolute top-0 left-0 right-0 bottom-0 z-10"></div>
		{/if}

		<div class="absolute pointer-events-none z-50 w-full flex items-center justify-start p-4">
			<button
				class="self-center pointer-events-auto p-1 rounded-full bg-white dark:bg-gray-850"
				on:click={() => {
					showArtifacts.set(false);
				}}
			>
				<ArrowLeft className="size-3.5  text-gray-900 dark:text-white" />
			</button>
		</div>

		<div class=" absolute pointer-events-none z-50 w-full flex items-center justify-end p-4">
			<button
				class="self-center pointer-events-auto p-1 rounded-full bg-white dark:bg-gray-850"
				on:click={() => {
					dispatch('close');
					showControls.set(false);
					showArtifacts.set(false);
				}}
			>
				<XMark className="size-3.5 text-gray-900 dark:text-white" />
			</button>
		</div>

		<div class="flex-1 w-full h-full">
			<div class=" h-full flex flex-col">
				{#if contents.length > 0}
					<div class="max-w-full w-full h-full">
						{#if contents[selectedContentIdx].type === 'iframe'}
							<iframe
								bind:this={iframeElement}
								title="Content"
								srcdoc={contents[selectedContentIdx].content}
								class="w-full border-0 h-full rounded-none"
								sandbox="allow-scripts allow-forms allow-same-origin"
								on:load={iframeLoadHandler}
							></iframe>
						{:else if contents[selectedContentIdx].type === 'svg'}
							<SvgPanZoom
								className=" w-full h-full max-h-full overflow-hidden"
								svg={contents[selectedContentIdx].content}
							/>
						{/if}
					</div>
				{:else}
					<div class="m-auto font-medium text-xs text-gray-900 dark:text-white">
						{$i18n.t('No content found.')}
					</div>
				{/if}
			</div>
		</div>
	</div>

	{#if contents.length > 0}
		<div class="flex justify-between items-center p-2.5 font-primar text-gray-900 dark:text-white">
			<div class="flex items-center space-x-2">
				<div class="flex items-center gap-0.5 self-center min-w-fit" dir="ltr">
					<button
						class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition disabled:cursor-not-allowed"
						on:click={() => navigateContent('prev')}
						disabled={contents.length <= 1}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							stroke-width="2.5"
							class="size-3.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M15.75 19.5 8.25 12l7.5-7.5"
							/>
						</svg>
					</button>

					<div class="text-xs self-center dark:text-gray-100 min-w-fit">
						{$i18n.t('Version {{selectedVersion}} of {{totalVersions}}', {
							selectedVersion: selectedContentIdx + 1,
							totalVersions: contents.length
						})}
					</div>

					<button
						class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition disabled:cursor-not-allowed"
						on:click={() => navigateContent('next')}
						disabled={contents.length <= 1}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							stroke-width="2.5"
							class="size-3.5"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
						</svg>
					</button>
				</div>
			</div>

			<div class="flex items-center gap-1">

				<button
                class="copy-code-button bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
                on:click={() => {
                    copyToClipboard(contents[selectedContentIdx].content);
                    copied = true;

                    setTimeout(() => {
                        copied = false;
                    }, 2000);
                }}>{copied ? $i18n.t('Copied') : $i18n.t('Copy')}</button
            >

				<button
					class="copy-code-button bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
					on:click={() => {
						viewMode = viewMode === 'Code' ? 'Design' : 'Code';

						getContents(true);
					}}
					>{$i18n.t('View ' + (viewMode === 'Code' ? 'Design' : 'Code'))}</button
				>

                <button
					class="copy-code-button bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
					on:click={() => {
						showDiffs = !showDiffs;
						getContents(true);
					}}
					>{$i18n.t((showDiffs ? 'Hide' : 'Show') + ' Comparison')}</button
				>

                <button
					class="copy-code-button bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
					on:click={() => {
						hideInline.set(!$hideInline);
					}}
					>{$i18n.t(($hideInline ? 'Hide' : 'Show') + ' In Chat')}</button
				>

				{#if contents[selectedContentIdx].type === 'iframe'}
					<Tooltip content={$i18n.t('Open in full screen')}>
						<button
							class=" bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md p-0.5"
							on:click={showFullScreen}
						>
							<ArrowsPointingOut className="size-3.5" />
						</button>
					</Tooltip>
				{/if}
			</div>
		</div>
	{/if}
</div>
