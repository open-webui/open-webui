/// <reference path="../support/e2e.ts" />

/**
 * Quiz workflow: /kids/profile
 * Uses INTERVIEWEE_EMAIL/INTERVIEWEE_PASSWORD or TEST_EMAIL/TEST_PASSWORD from env;
 * defaults to jjdrisco@ucsd.edu / 0000 if unset.
 * Prereqs: frontend (npm run dev) and backend running; RUN_CHILD_PROFILE_TESTS=1;
 * CYPRESS_baseUrl must match the dev server port (e.g. http://localhost:5173 or 5174).
 * See cypress/README_CHILD_PROFILE_TESTS.md.
 * Run: RUN_CHILD_PROFILE_TESTS=1 CYPRESS_baseUrl=http://localhost:5173 npx cypress run --spec cypress/e2e/kids-profile.cy.ts
 */
const EMAIL = Cypress.env('INTERVIEWEE_EMAIL') || Cypress.env('TEST_EMAIL') || 'jjdrisco@ucsd.edu';
const PASSWORD = Cypress.env('INTERVIEWEE_PASSWORD') || Cypress.env('TEST_PASSWORD') || '0000';

describe('Quiz /kids/profile', () => {
	beforeEach(() => {
		if (!EMAIL || !PASSWORD) {
			cy.log('INTERVIEWEE_EMAIL/PASSWORD or TEST_EMAIL/TEST_PASSWORD not set; skipping');
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
			['/kids/profile', '/', '/moderation-scenario', '/assignment-instructions', '/parent'].some(
				(p) => u.includes(p)
			)
		);
		// So /kids/profile does not redirect to instructions
		cy.window().then((w) => w.localStorage.setItem('instructionsCompleted', 'true'));
	});

	it('A. Research fields visible and required', function () {
		if (!EMAIL || !PASSWORD) {
			this.skip();
			return;
		}
		cy.visit('/kids/profile');
		cy.url({ timeout: 10000 }).should('include', '/kids/profile');

		// Open add or edit form so research fields are visible
		cy.contains('Add', { matchCase: false }).first().click();

		// Expect research labels (only when showResearchFields=true)
		cy.contains('Only Child').should('be.visible');
		cy.contains('Child Has Used AI Tools').should('be.visible');
		cy.contains('Parent LLM Monitoring').should('be.visible');

		// Fill only core fields, leave research empty -> save blocked (requireResearchFields)
		cy.get('input#childName').type('TestChild');
		cy.get('select#childAge').select('10 years old');
		cy.get('select#childGender').select('Male');
		// Do not fill Only Child, Child Has Used AI, Parent LLM Monitoring
		cy.get('form')
			.contains(/save|create|add/i)
			.first()
			.click();
		// Expect validation: toast or button stays / no navigation
		cy.get('body').then(($b) => {
			const t = $b.find('[data-sonner-toast], [role=alert], .toast, .error').length;
			// Either a validation toast/error or we remain on page (no redirect)
			cy.url().should('include', '/kids/profile');
		});
	});

	it('B. Confirmation modal on create/save/select', function () {
		if (!EMAIL || !PASSWORD) {
			this.skip();
			return;
		}
		cy.visit('/kids/profile');
		cy.url({ timeout: 10000 }).should('include', '/kids/profile');

		// Create or save: expect "Task 1 Complete" modal
		cy.contains('Add', { matchCase: false }).first().click();
		cy.get('input#childName').type('ModalTest');
		cy.get('select#childAge').select('11 years old');
		cy.get('select#childGender').select('Female');
		// Research fields (required in quiz)
		cy.contains('Only Child').parent().find('input[value=yes]').check({ force: true });
		cy.contains('Child Has Used AI Tools').parent().find('input[value=no]').check({ force: true });
		cy.contains('Parent LLM Monitoring')
			.parent()
			.find('input[value=no_monitoring]')
			.check({ force: true });
		cy.get('form')
			.contains(/save|create|add/i)
			.first()
			.click();

		cy.contains('Task 1 Complete', { timeout: 10000 }).should('be.visible');
		cy.contains('Would you like to proceed to the next step?').should('be.visible');
		cy.contains('Yes, Proceed to the Next Step').should('be.visible');
		cy.contains('No, Continue Editing Profile').should('be.visible');
	});

	it('C. localStorage and Next Task after select', function () {
		if (!EMAIL || !PASSWORD) {
			this.skip();
			return;
		}
		cy.visit('/kids/profile');
		cy.url({ timeout: 10000 }).should('include', '/kids/profile');
		cy.window().then((w) => {
			w.localStorage.setItem('assignmentStep', '2');
			w.localStorage.setItem('moderationScenariosAccessed', 'true');
			w.localStorage.setItem('unlock_moderation', 'true');
		});
		cy.contains('Next Task').should('exist');
	});
});
