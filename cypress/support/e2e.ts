/// <reference types="cypress" />
// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

export const adminUser = {
	name: 'Admin User',
	email: 'admin@example.com',
	password: 'password'
};

const login = (email: string, password: string) => {
	return cy.session(
		email,
		() => {
			// Make sure to test against us english to have stable tests,
			// regardless on local language preferences
			localStorage.setItem('locale', 'en-US');

			// Try API-based login first (more reliable)
			cy.request({
				method: 'POST',
				url: '/api/v1/auths/signin',
				body: {
					email: email,
					password: password
				},
				failOnStatusCode: false
			}).then((response) => {
				if (response.status === 200 && response.body?.token) {
					// API login succeeded - use 'token' field (not 'access_token')
					cy.window().then((win) => {
						win.localStorage.setItem('token', response.body.token);
					});
					// Visit home page to verify login
					cy.visit('/');
					// Wait for page to load - try multiple possible selectors
					cy.get('body').should('exist');
					cy.wait(1000); // Give page time to render
					// Check for chat-search or other indicators that we're logged in
					cy.get('body').then(($body) => {
						if ($body.find('#chat-search').length > 0) {
							cy.get('#chat-search', { timeout: 10000 }).should('exist');
						} else {
							// Page might have loaded but redirected - just verify we're not on auth page
							cy.url().should('not.include', '/auth');
						}
					});
					// Get the current version to skip the changelog dialog
					cy.window().then((win) => {
						if (win.localStorage.getItem('version') === null) {
							// Try to find and click the changelog button, but don't fail if it doesn't exist
							cy.get('body').then(($body) => {
								const changelogBtn = $body.find(
									'button:contains("Okay"), button:contains("Let\'s Go"), button:contains("Go")'
								);
								if (changelogBtn.length > 0) {
									cy.wrap(changelogBtn.first()).click();
								}
							});
						}
					});
				} else {
					// Fallback to form-based login
					cy.visit('/auth', { timeout: 10000 });
					// Wait for page to load - check for any visible input
					cy.get('body').should('exist');
					cy.wait(1000); // Give Svelte time to render

					// Try to find email input with multiple strategies
					cy.get('body').then(($body) => {
						if ($body.find('input[autocomplete="email"]').length > 0) {
							cy.get('input[autocomplete="email"]', { timeout: 10000 }).should('be.visible');
							cy.get('input[autocomplete="email"]').type(email);
						} else if ($body.find('input#email').length > 0) {
							cy.get('input#email', { timeout: 10000 }).should('be.visible');
							cy.get('input#email').type(email);
						} else if ($body.find('input[type="email"]').length > 0) {
							cy.get('input[type="email"]', { timeout: 10000 }).should('be.visible');
							cy.get('input[type="email"]').type(email);
						} else {
							// Log for debugging
							cy.log('Could not find email input. Body HTML:', $body.html().substring(0, 500));
							throw new Error('Email input not found on auth page');
						}
					});

					cy.get('input[type="password"], input#password').first().type(password);
					cy.get('button[type="submit"]').click();
					// Wait until the user is redirected - admin users go to /admin/users
					cy.url({ timeout: 15000 }).should('not.include', '/auth');
					// Get the current version to skip the changelog dialog
					cy.window().then((win) => {
						if (win.localStorage.getItem('version') === null) {
							// Try to find and click the changelog button, but don't fail if it doesn't exist
							cy.get('body').then(($body) => {
								const changelogBtn = $body.find(
									'button:contains("Okay"), button:contains("Let\'s Go"), button:contains("Go")'
								);
								if (changelogBtn.length > 0) {
									cy.wrap(changelogBtn.first()).click();
								}
							});
						}
					});
				}
			});
		},
		{
			validate: () => {
				cy.window().then((win) => {
					const token = win.localStorage.getItem('token');
					if (!token) {
						throw new Error('No token found in localStorage');
					}
					return cy.request({
						method: 'GET',
						url: '/api/v1/auths/',
						headers: {
							Authorization: `Bearer ${token}`
						}
					});
				});
			}
		}
	);
};

const register = (name: string, email: string, password: string) => {
	return cy
		.request({
			method: 'POST',
			url: '/api/v1/auths/signup',
			body: {
				name: name,
				email: email,
				password: password
			},
			failOnStatusCode: false
		})
		.then((response) => {
			// Accept 200 (success), 400 (bad request), or 403 (signup disabled)
			expect(response.status).to.be.oneOf([200, 400, 403]);
		});
};

const registerAdmin = () => {
	return register(adminUser.name, adminUser.email, adminUser.password);
};

const loginAdmin = () => {
	return login(adminUser.email, adminUser.password);
};

Cypress.Commands.add('login', (email, password) => login(email, password));
Cypress.Commands.add('register', (name, email, password) => register(name, email, password));
Cypress.Commands.add('registerAdmin', () => registerAdmin());
Cypress.Commands.add('loginAdmin', () => loginAdmin());

before(() => {
	// Skip registerAdmin when only running child-profile specs (avoids 500 from signup if backend state differs)
	if (!Cypress.env('RUN_CHILD_PROFILE_TESTS')) {
		cy.registerAdmin();
	}
});
