// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// These tests run through the chat flow.
describe('Settings', () => {
	// Wait for 2 seconds after all tests to fix an issue with Cypress's video recording missing the last few frames
	after(() => {
		// eslint-disable-next-line cypress/no-unnecessary-waiting
		cy.wait(2000);
	});

	beforeEach(() => {
		// Login as the admin user
		cy.loginAdmin();
		// Visit the home page
		cy.visit('/');
	});

	context('Ollama', () => {
		it('user can select a model', () => {
			// Click on the model selector
			cy.get('button[aria-label="Select a model"]').click();
			// Select the first model
			cy.get('button[aria-roledescription="model-item"]').first().click();
		});

		it('user can perform text chat', () => {
			// Click on the model selector
			cy.get('button[aria-label="Select a model"]').click();
			// Select the first model
			cy.get('button[aria-roledescription="model-item"]').first().click();
			// Type a message
			cy.get('#chat-input').type('Hi, what can you do? A single sentence only please.', {
				force: true
			});
			// Send the message
			cy.get('button[type="submit"]').click();
			// User's message should be visible
			cy.get('.chat-user').should('exist');
			// Wait for the response
			// .chat-assistant is created after the first token is received
			cy.get('.chat-assistant', { timeout: 10_000 }).should('exist');
			// Generation Info is created after the stop token is received
			cy.get('div[aria-label="Generation Info"]', { timeout: 120_000 }).should('exist');
		});

		it('user can share chat', () => {
			// Click on the model selector
			cy.get('button[aria-label="Select a model"]').click();
			// Select the first model
			cy.get('button[aria-roledescription="model-item"]').first().click();
			// Type a message
			cy.get('#chat-input').type('Hi, what can you do? A single sentence only please.', {
				force: true
			});
			// Send the message
			cy.get('button[type="submit"]').click();
			// User's message should be visible
			cy.get('.chat-user').should('exist');
			// Wait for the response
			// .chat-assistant is created after the first token is received
			cy.get('.chat-assistant', { timeout: 10_000 }).should('exist');
			// Generation Info is created after the stop token is received
			cy.get('div[aria-label="Generation Info"]', { timeout: 120_000 }).should('exist');
			// spy on requests
			const spy = cy.spy();
			cy.intercept('POST', '/api/v1/chats/**/share', spy);
			// Open context menu
			cy.get('#chat-context-menu-button').click();
			// Click share button
			cy.get('#chat-share-button').click();
			// Check if the share dialog is visible
			cy.get('#copy-and-share-chat-button').should('exist');
			// Click the copy button
			cy.get('#copy-and-share-chat-button').click();
			cy.wrap({}, { timeout: 5_000 }).should(() => {
				// Check if the share request was made
				expect(spy).to.be.callCount(1);
			});
		});

		it('user can generate image', () => {
			// Click on the model selector
			cy.get('button[aria-label="Select a model"]').click();
			// Select the first model
			cy.get('button[aria-roledescription="model-item"]').first().click();
			// Type a message
			cy.get('#chat-input').type('Hi, what can you do? A single sentence only please.', {
				force: true
			});
			// Send the message
			cy.get('button[type="submit"]').click();
			// User's message should be visible
			cy.get('.chat-user').should('exist');
			// Wait for the response
			// .chat-assistant is created after the first token is received
			cy.get('.chat-assistant', { timeout: 10_000 }).should('exist');
			// Generation Info is created after the stop token is received
			cy.get('div[aria-label="Generation Info"]', { timeout: 120_000 }).should('exist');
			// Click on the generate image button
			cy.get('[aria-label="Generate Image"]').click();
			// Wait for image to be visible
			cy.get('img[data-cy="image"]', { timeout: 60_000 }).should('be.visible');
		});

		it('user can pin, navigate, persist, and unpin conversation anchors', () => {
			// Select a model first
			cy.get('button[aria-label="Select a model"]').click();
			cy.get('button[aria-roledescription="model-item"]').first().click();

			// Send a prompt and wait for assistant response
			cy.get('#chat-input').type('Reply in one short paragraph about cypress testing.', {
				force: true
			});
			cy.get('button[type="submit"]').click();
			cy.get('.chat-assistant', { timeout: 10_000 }).should('exist');
			cy.get('div[aria-label="Generation Info"]', { timeout: 120_000 }).should('exist');

			let selectedSnippet = '';

			// Programmatically select text inside the first assistant response and trigger mouseup
				cy.window().then((win) => {
					const responseRoot = win.document.querySelector(
						'.chat-assistant #response-content-container'
					) as HTMLElement | null;
					if (!responseRoot) {
						throw new Error('Assistant response container not found');
					}

					const walker = win.document.createTreeWalker(responseRoot, win.NodeFilter.SHOW_TEXT, {
						acceptNode: (node: Node) =>
							(node.textContent ?? '').trim().length > 20
								? win.NodeFilter.FILTER_ACCEPT
								: win.NodeFilter.FILTER_SKIP
					});

					const textNode = walker.nextNode() as Text | null;
					if (!textNode) {
						throw new Error('No assistant text node found for selection');
					}

				selectedSnippet = (textNode.textContent ?? '').trim().slice(0, 16);
				expect(selectedSnippet.length).to.be.greaterThan(5);

				const range = win.document.createRange();
				range.setStart(textNode, 0);
				range.setEnd(textNode, selectedSnippet.length);

				const selection = win.getSelection();
				selection?.removeAllRanges();
				selection?.addRange(range);

				responseRoot.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
			});

			// Pin selected snippet from floating actions
			cy.contains('button', 'Pin', { timeout: 10_000 }).click();

			// Verify pinned section and item
			cy.contains('Pinned Messages').should('exist');
			cy.contains('Pinned Messages')
				parents('div')
				.first()
				within(() => {
					cy.contains(selectedSnippet).should('exist');
				});

			// Reload and verify persistence
			cy.reload();
			cy.contains('Pinned Messages').should('exist');
			cy.contains('Pinned Messages')
				parents('div')
				.first()
				within(() => {
					cy.contains(selectedSnippet).should('exist');
				});

			// Click pinned item and verify target highlight behavior appears
			cy.contains(selectedSnippet).click();
			cy.get('[data-pin-snippet-id]', { timeout: 5_000 }).should('exist');

			// Unpin from sidebar
			cy.contains('Pinned Messages')
				parents('div')
				.first()
				.within(() => {
					cy.contains(selectedSnippet).should('exist');
					cy.get('button[aria-label="Unpin"]').first().click({ force: true });
				});
			cy.contains('Pinned Messages').should('not.exist');

			// Reload and ensure unpinned state persists
			cy.reload();
			cy.contains('Pinned Messages').should('not.exist');
		});
	});
});
