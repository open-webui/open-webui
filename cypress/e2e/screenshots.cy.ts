// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

describe('Screenshots', () => {
	after(() => {
		// eslint-disable-next-line cypress/no-unnecessary-waiting
		cy.wait(2000);
	});

	beforeEach(() => {
		cy.loginAdmin();
	});

	it('home — new chat screen', () => {
		cy.visit('/');
		cy.get('#chat-search').should('exist');
		cy.screenshot('home', { capture: 'fullPage' });
	});

	it('sidebar — open with recents and nav', () => {
		cy.visit('/');
		cy.get('#chat-search').should('exist');
		// Ensure sidebar is open (toggle if needed)
		cy.get('body').then(($body) => {
			if ($body.find('#sidebar').length === 0 || $body.find('#sidebar').is(':hidden')) {
				cy.get('button[aria-label="Open sidebar"]').click({ force: true });
			}
		});
		cy.screenshot('sidebar', { capture: 'fullPage' });
	});

	it('settings — settings panel', () => {
		cy.visit('/');
		cy.get('#chat-search').should('exist');
		// Open user menu and navigate to settings
		cy.get('button[aria-label="User Menu"]').click({ force: true });
		cy.get('button').contains('Settings').click({ force: true });
		cy.get('[data-testid="settings-modal"], dialog, [role="dialog"]', { timeout: 5000 }).should(
			'exist'
		);
		cy.screenshot('settings', { capture: 'fullPage' });
	});
});
