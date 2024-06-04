// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// These tests run through the chat flow.
describe('Chat', () => {
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
			cy.get('button[aria-label="model-item"]').first().click();
		});

		it('user can perform text chat', () => {
			// Click on the model selector
			cy.get('button[aria-label="Select a model"]').click();
			// Select the first model
			cy.get('button[aria-label="model-item"]').first().click();
			// Type a message
			cy.get('#chat-textarea').type('Hi, what can you do? A single sentence only please.', {
				force: true
			});
			// Send the message
			cy.get('button[type="submit"]').click();
			// User's message should be visible
			cy.get('.chat-user').should('exist');
			// Wait for the response
			cy.get('.chat-assistant', { timeout: 120_000 }) // .chat-assistant is created after the first token is received
				.find('div[aria-label="Edit"]', { timeout: 120_000 }) // Edit is created after the stop token is received
				.should('exist');
		});

		it('user can share chat', () => {
			// Click on the model selector
			cy.get('button[aria-label="Select a model"]').click();
			// Select the first model
			cy.get('button[aria-label="model-item"]').first().click();
			// Type a message
			cy.get('#chat-textarea').type('Hi, what can you do? A single sentence only please.', {
				force: true
			});
			// Send the message
			cy.get('button[type="submit"]').click();
			// User's message should be visible
			cy.get('.chat-user').should('exist');
			// Wait for the response
			cy.get('.chat-assistant', { timeout: 120_000 }) // .chat-assistant is created after the first token is received
				.find('div[aria-label="Edit"]', { timeout: 120_000 }) // Edit is created after the stop token is received
				.should('exist');
			// spy on requests
			const spy = cy.spy();
			cy.intercept('GET', '/api/v1/chats/*', spy);
			// Open context menu
			cy.get('#chat-context-menu-button').click();
			// Click share button
			cy.get('#chat-share-button').click();
			// Check if the share dialog is visible
			cy.get('#copy-and-share-chat-button').should('exist');
			cy.wrap({}, { timeout: 5000 }).should(() => {
				// Check if the request was made twice (once for to replace chat object and once more due to change event)
				expect(spy).to.be.callCount(2);
			});
		});

		it('user can generate image', () => {
			// Click on the model selector
			cy.get('button[aria-label="Select a model"]').click();
			// Select the first model
			cy.get('button[aria-label="model-item"]').first().click();
			// Type a message
			cy.get('#chat-textarea').type('Hi, what can you do? A single sentence only please.', {
				force: true
			});
			// Send the message
			cy.get('button[type="submit"]').click();
			// User's message should be visible
			cy.get('.chat-user').should('exist');
			// Wait for the response
			cy.get('.chat-assistant', { timeout: 120_000 }) // .chat-assistant is created after the first token is received
				.find('div[aria-label="Edit"]', { timeout: 120_000 }) // Edit is created after the stop token is received
				.should('exist');
			// Click on the generate image button
			cy.get('[aria-label="Generate Image"]').click();
			// Wait for image to be visible
			cy.get('img[data-cy="image"]', { timeout: 60_000 }).should('be.visible');
		});
	});

	context('Missing documents', () => {
		const suffix = Date.now().toString();
		const documentFileName: string = `test-${suffix}.txt`;
		const documentTitle: string = `test${suffix}txt`;

		beforeEach(() => {
			// Login as the admin user
			cy.loginAdmin();
			// Go to documents
			cy.visit('/workspace/documents');
			// open document add modal dialog
			cy.get('button[aria-label="Add Docs"]').click();
			// Create a document
			cy.readFile('cypress/data/example-doc.txt').then((text) => {
				// select file
				cy.get('#upload-doc-input').selectFile(
					{
						contents: Cypress.Buffer.from(text + Date.now()),
						fileName: documentFileName,
						mimeType: 'text/plain',
						lastModified: Date.now()
					},
					{
						force: true
					}
				);
				// open tag input
				cy.get('#add-tag-button').click();
				cy.get("input[placeholder='Add a tag']").type('cypress-test');
				cy.get('#save-tag-button').click();

				// submit to upload
				cy.get("button[type='submit']").click();
			});
			// wait for upload
			cy.get('.document-entry').contains(documentTitle).should('exist');
		});

		it('shows warning on missing document', () => {
			cy.get('.document-entry').should('exist');

			// go to home
			cy.visit('/');
			// Click on the model selector
			cy.get('button[aria-label="Select a model"]').click();
			// Select the first model
			cy.get('button[aria-label="model-item"]').first().click();
			// Type a message

			// Type file tag name
			cy.get('#chat-textarea').type(`#${documentTitle}`, {
				force: true
			});
			// select file
			cy.get('button').contains(documentTitle).click();
			// type question
			cy.get('#chat-textarea').type(`How many times does the word Lorem occur?`, {
				force: true
			});
			// Send the message
			cy.get('button[type="submit"]').click();
			// User's message should be visible
			cy.get('.chat-user').should('exist');
			// Wait for the response
			cy.get('.chat-assistant', { timeout: 120_000 }) // .chat-assistant is created after the first token is received
				.find('div[aria-label="Edit"]', { timeout: 120_000 }) // Generation Info is not always created after the stop token is received. Use edit instead
				.should('exist');
			cy.location('pathname')
				.should('match', /\/c\/.*/)
				.then((url) => url)
				.as('chatUrl');

			// go back to documents
			cy.visit('/workspace/documents');

			// reset vector db
			cy.get('button[aria-label="Document Settings"]').click();
			cy.get('button[aria-label="Reset Vector Storage"').click();
			cy.get('button[aria-label="Confirm"').click();

			// go back to chat
			cy.get('@chatUrl').then((url: any) => {
				cy.log(url);
				cy.visit(url);
			});

			// ask another question
			cy.get('#chat-textarea').type(`How many times does the word Lorem occur?`, {
				force: true
			});
			// Send the message
			cy.get('button[type="submit"]').click();
			// User's message should be visible
			cy.get('.chat-user').should('exist');
			// Wait for the response
			cy.get('.chat-assistant', { timeout: 120_000 }) // .chat-assistant is created after the first token is received
				.find('div[aria-label="Edit"]', { timeout: 120_000 }) // Generation Info is not always created after the stop token is received. Use edit instead
				.should('exist');
			cy.location('pathname')
				.should('match', /\/c\/.*/)
				.then((url) => url)
				.as('chatUrl');

			// check if alert is visible
			cy.get('span[role=alert]').should(
				'contain.text',
				'At least one file in your conversation does not exist any more. The following answer may be incomplete.'
			);
		});
	});
});
