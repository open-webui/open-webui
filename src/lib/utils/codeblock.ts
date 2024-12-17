import { copyToClipboard } from './index';
import { toast } from 'svelte-sonner';

export function createCopyCodeBlockButton() {
    const codeBlocks = document.querySelectorAll('pre code');
    codeBlocks.forEach((codeBlock) => {
        const container = codeBlock.parentElement;
        if (!container) return;

        // Check if button already exists
        if (container.querySelector('.copy-button')) return;

        const button = document.createElement('button');
        button.className = 'copy-button absolute right-2 top-2 p-1 rounded text-sm bg-gray-700 hover:bg-gray-600 text-white';
        button.textContent = 'Copy';

        button.addEventListener('click', async () => {
            const code = codeBlock.textContent || '';
            await copyToClipboard(code);
            button.textContent = 'Copied!';
            toast.success('Code copied to clipboard');
            setTimeout(() => {
                button.textContent = 'Copy';
            }, 2000);
        });

        // Make container relative for absolute positioning of button
        container.style.position = 'relative';
        container.appendChild(button);
    });
}
