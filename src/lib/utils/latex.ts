import katex from 'katex';
import 'katex/contrib/mhchem';
import 'katex/dist/katex.min.css';

export function renderLatex() {
    const elements = document.getElementsByClassName('math');
    for (let i = 0; i < elements.length; i++) {
        const element = elements[i];
        try {
            const content = element.textContent || '';
            const displayMode = element.classList.contains('display');
            katex.render(content, element, {
                displayMode,
                throwOnError: false,
                output: 'html'
            });
        } catch (error) {
            console.error('Error rendering LaTeX:', error);
        }
    }
}
