// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// Short, predictable prompts that produce brief responses.
const PROMPTS = [
	"Reply with exactly: 'Exchange 1 done'.",
	"Reply with exactly: 'Exchange 2 done'.",
	"Reply with exactly: 'Exchange 3 done'.",
	"Reply with exactly: 'Exchange 4 done'.",
	"Reply with exactly: 'Exchange 5 done'.",
	"Reply with exactly: 'Exchange 6 done'."
];

/**
 * Send a message and wait until the assistant finishes responding.
 * The Copy button (aria-label="Copy") only renders when message.done is true.
 */
const exchange = (text: string) => {
	cy.get('#chat-input').type(text, { force: true });
	cy.get('button[type="submit"]').click();
	cy.get('.chat-user').should('exist');
	cy.get('.chat-assistant button[aria-label="Copy"]', { timeout: 120_000 }).last().should('exist');
};

describe('Chat', () => {
	after(() => {
		// Give Cypress video recording time to capture the last frame
		// eslint-disable-next-line cypress/no-unnecessary-waiting
		cy.wait(2000);
	});

	beforeEach(() => {
		cy.loginAdmin();
		cy.visit('/');
	});

	it('new chat — 3 exchanges, sidebar → recent chat — 3 exchanges, post screenshots, delete chats', () => {
		// === 1. New chat — 3 exchanges ===
		exchange(PROMPTS[0]);
		exchange(PROMPTS[1]);
		exchange(PROMPTS[2]);

		// Capture the chat ID so we can delete it at the end
		cy.url().should('include', '/c/');
		cy.screenshot('1-new-chat-3-exchanges', { capture: 'fullPage' });

		// === 2. Navigate to new chat, then use sidebar to return to recent chat ===
		cy.get('a[aria-label="New Chat"]').first().click();
		cy.url().should('not.include', '/c/');

		// The first sidebar item is the chat we just created
		cy.get('a[id="sidebar-chat-item"]').first().click();
		cy.url().should('include', '/c/');

		// === 3. Three more exchanges in the recent chat ===
		exchange(PROMPTS[3]);
		exchange(PROMPTS[4]);
		exchange(PROMPTS[5]);

		cy.screenshot('2-sidebar-recent-chat-3-exchanges', { capture: 'fullPage' });

		// === 4. Post screenshots to #otto-dev and wait for feedback ===
		// Blocks until user replies in #otto-dev channel (up to 60 min).
		// The feedback text is printed to stdout for Claude to read and iterate on.
		cy.exec('bash scripts/post-channel.sh --dir=cypress/screenshots', {
			timeout: 3_600_000,
			failOnNonZero: false
		}).its('stdout').then((feedback) => {
			cy.log('Feedback: ' + feedback);
		});

		// === 5. Delete all chats created during this test ===
		// Collect chat IDs from sidebar items and delete each via API
		cy.get('a[id="sidebar-chat-item"]').then(($items) => {
			const token = localStorage.getItem('token') ?? '';
			$items.each((_i, el) => {
				const href = el.getAttribute('href') ?? '';
				const id = href.split('/c/')[1];
				if (id) {
					cy.request({
						method: 'DELETE',
						url: `/api/v1/chats/${id}`,
						headers: { authorization: `Bearer ${token}` },
						failOnStatusCode: false
					});
				}
			});
		});
	});
});
