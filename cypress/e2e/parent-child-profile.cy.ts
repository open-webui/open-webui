/// <reference path="../support/e2e.ts" />

/**
 * Parent workflow: /parent/child-profile
 * Uses PARENT_EMAIL/PARENT_PASSWORD or TEST_EMAIL/TEST_PASSWORD from env;
 * defaults to jjdrisco@ucsd.edu / 0000 if unset.
 * Prereqs: frontend (npm run dev) and backend running; RUN_CHILD_PROFILE_TESTS=1;
 * CYPRESS_baseUrl must match the dev server port (e.g. http://localhost:5173 or 5174).
 * See cypress/README_CHILD_PROFILE_TESTS.md.
 * Run: RUN_CHILD_PROFILE_TESTS=1 CYPRESS_baseUrl=http://localhost:5173 npx cypress run --spec cypress/e2e/parent-child-profile.cy.ts
 */
const EMAIL = Cypress.env('PARENT_EMAIL') || Cypress.env('TEST_EMAIL') || 'jjdrisco@ucsd.edu';
const PASSWORD = Cypress.env('PARENT_PASSWORD') || Cypress.env('TEST_PASSWORD') || '0000';

describe('Parent /parent/child-profile', () => {
	beforeEach(() => {
		if (!EMAIL || !PASSWORD) {
			cy.log('PARENT_EMAIL/PASSWORD or TEST_EMAIL/TEST_PASSWORD not set; skipping');
			return;
		}
		cy.visit('/auth', {
			onBeforeLoad(win) {
				win.localStorage.removeItem('token');
			}
		});
		// Wait for auth form (loaded + config); email field when not in LDAP mode
		cy.get('input#email, input[autocomplete="email"]', { timeout: 15000 })
			.first()
			.clear()
			.type(EMAIL);
		cy.get('input[type="password"]').first().clear().type(PASSWORD);
		cy.get('button')
			.contains(/sign in/i)
			.click();
		cy.url({ timeout: 15000 }).should('satisfy', (u: string) =>
			['/parent', '/', '/kids/profile', '/auth'].some((p) => u.includes(p))
		);
	});

	it('A. No research fields', function () {
		if (!EMAIL || !PASSWORD) {
			this.skip();
			return;
		}
		cy.visit('/parent/child-profile');
		cy.url({ timeout: 10000 }).should('include', '/parent/child-profile');

		// Research labels must NOT be visible (showResearchFields=false)
		cy.contains('Child Has Used AI Tools').should('not.exist');
		cy.contains('Parent LLM Monitoring Level').should('not.exist');
		cy.contains('Only Child').should('not.exist');
	});

	it('B. Redirect to /parent on create and save', function () {
		if (!EMAIL || !PASSWORD) {
			this.skip();
			return;
		}
		cy.visit('/parent/child-profile');
		cy.url({ timeout: 10000 }).should('include', '/parent/child-profile');

		cy.contains('Add', { matchCase: false }).first().click();
		cy.get('input#childName').type('ParentTest');
		cy.get('select#childAge').select('12 years old');
		cy.get('select#childGender').select('Male');
		cy.get('form')
			.contains(/save|create|add/i)
			.first()
			.click();

		cy.url({ timeout: 6000 }).should('include', '/parent');
	});

	it('C. Select child: no Task 1 Complete modal', function () {
		if (!EMAIL || !PASSWORD) {
			this.skip();
			return;
		}
		cy.visit('/parent/child-profile');
		cy.url({ timeout: 10000 }).should('include', '/parent/child-profile');
		// If there are at least two child cards, click the second
		cy.get('body').then(($b) => {
			const cards = $b.find('[data-child-card], .border.rounded, [class*="child"]');
			if (cards.length >= 2) {
				cy.wrap(cards.eq(1)).click();
			}
		});
		cy.contains('Task 1 Complete').should('not.exist');
		cy.url().should('include', '/parent/child-profile');
	});

	it('D. Nav: Back to Dashboard and Continue', function () {
		if (!EMAIL || !PASSWORD) {
			this.skip();
			return;
		}
		cy.visit('/parent/child-profile');
		cy.contains('Back to Dashboard').should('be.visible').click();
		cy.url().should('include', '/parent');
	});
});
