import * as ReactDOM from 'react-dom/client';
import BlockNote from './BlockNote';

class MyReactWrapper extends HTMLElement {
	private root: ReactDOM.Root | null = null;

	connectedCallback() {
		// Only create a new root if one doesn't exist
		if (!this.root) {
			this.root = ReactDOM.createRoot(this);
		}

		// Render or re-render with current content
		this.render();
	}

	disconnectedCallback() {
		// Clean up the React root when element is removed
		if (this.root) {
			this.root.unmount();
			this.root = null;
		}
	}

	attributeChangedCallback(name: string, oldValue: string, newValue: string) {
		console.log('attributeChangedCallback');
		// Re-render when content attribute changes
		if (name === 'content' && oldValue !== newValue) {
			console.log('rerender');
			this.render();
		}
	}

	static get observedAttributes() {
		return ['content'];
	}

	private render() {
		if (this.root) {
			console.log('rendering content: ', this.getAttribute('content'));
			// this.root.render(<div data-content={this.getAttribute('content') || ''}>hello</div>);
			this.root.render(<BlockNote content={this.getAttribute('content') || ''} />);
		}
	}
}

customElements.define('blocknote-wrapper', MyReactWrapper);

export default '';
