// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { adminUser } from '../support/e2e';

// These tests assume the following defaults:
// 1. No users exist in the database or that the test admin user is an admin
// 2. Language is set to English
// 3. The default role for new users is 'pending'
describe('Registration and Login', () => {
	// Wait for 2 seconds after all tests to fix an issue with Cypress's video recording missing the last few frames
	after(() => {
		// eslint-disable-next-line cypress/no-unnecessary-waiting
		cy.wait(2000);
	});

	beforeEach(() => {
		cy.visit('/');
	});

	it('should register a new user as pending', () => {
		const userName = `Test User - ${Date.now()}`;
		const userEmail = `cypress-${Date.now()}@example.com`;
		// Toggle from sign in to sign up
		cy.contains('Sign up').click();
		// Fill out the form
		cy.get('input[autocomplete="name"]').type(userName);
		cy.get('input[autocomplete="email"]').type(userEmail);
		cy.get('input[type="password"]').type('password');
		// Submit the form
		cy.get('button[type="submit"]').click();
		// Wait until the user is redirected to the home page
		cy.contains(userName);
		// Expect the user to be pending
		cy.contains('Check Again');
	});

	it('can login with the admin user', () => {
		// Fill out the form
		cy.get('input[autocomplete="email"]').type(adminUser.email);
		cy.get('input[type="password"]').type(adminUser.password);
		// Submit the form
		cy.get('button[type="submit"]').click();
		// Wait until the user is redirected to the home page
		cy.contains(adminUser.name);
		// Dismiss the changelog dialog if it is visible
		cy.getAllLocalStorage().then((ls) => {
			if (!ls['version']) {
				cy.get('button').contains("Okay, Let's Go!").click();
			}
		});
	});

	it('routes to resume step after sign in', () => {
		cy.visit('/auth?redirect=%2F');
		cy.contains(/sign in/i).should('exist');

		const EMAIL = Cypress.env('TEST_EMAIL') || adminUser.email;
		const PASSWORD = Cypress.env('TEST_PASSWORD') || adminUser.password;

		cy.get('input[type="email"]').clear().type(EMAIL);
		cy.get('input[type="password"]').first().clear().type(PASSWORD);
		cy.get('button').contains(/sign in/i).click();

		cy.location('pathname', { timeout: 15000 }).should((path) => {
			expect(['/kids/profile', '/moderation-scenario', '/exit-survey', '/completion', '/']).to.include(path);
		});
	});
});
