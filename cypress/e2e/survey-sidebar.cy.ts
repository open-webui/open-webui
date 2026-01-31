// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />
import { adminUser } from '../support/e2e';

describe('Survey Sidebar and Navigation', () => {
	// Wait for 2 seconds after all tests to fix an issue with Cypress's video recording missing the last few frames
	after(() => {
		// eslint-disable-next-line cypress/no-unnecessary-waiting
		cy.wait(2000);
	});

	beforeEach(() => {
		// Login as the admin user
		cy.loginAdmin();
		cy.wait(1000);
	});

	context('Admin Landing Page Redirect', () => {
		it('should redirect admin users to main chat page (/) instead of /admin/users', () => {
			// Visit the root page
			cy.visit('/', { failOnStatusCode: false });
			
			// Wait for redirect
			cy.wait(2000);
			
			// Should not be on /admin/users
			cy.url({ timeout: 10000 }).should('not.include', '/admin/users');
			
			// Should be on main chat page (either / or /c/[id])
			cy.url().then((url) => {
				expect(url).to.satisfy((u: string) => {
					return u === Cypress.config().baseUrl + '/' || u.includes('/c/');
				});
			});
		});
	});

	context('Survey Sidebar Visibility', () => {
		it('should show survey sidebar on exit-survey page', () => {
			// Navigate to exit-survey page
			cy.visit('/exit-survey', { failOnStatusCode: false });
			cy.wait(2000);
			
			// Check if survey sidebar exists
			cy.get('#survey-sidebar-nav, [id*="survey-sidebar"]', { timeout: 10000 }).should('exist');
			
			// Main sidebar should not be visible (or survey sidebar should be visible instead)
			// The survey sidebar should have the user menu
			cy.get('img[aria-label*="User Profile"], img[aria-label*="User Menu"]').should('exist');
		});

		it('should show survey sidebar on initial-survey page', () => {
			// Navigate to initial-survey page
			cy.visit('/initial-survey', { failOnStatusCode: false });
			cy.wait(2000);
			
			// Check if survey sidebar exists
			cy.get('#survey-sidebar-nav, [id*="survey-sidebar"]', { timeout: 10000 }).should('exist');
		});

		it('should show main sidebar on regular chat pages', () => {
			// Navigate to a regular page (not survey)
			cy.visit('/', { failOnStatusCode: false });
			cy.wait(2000);
			
			// Main sidebar should exist (not survey sidebar)
			// The main sidebar has different structure, check for chat-related elements
			cy.get('body').then(($body) => {
				// Main sidebar should be present (it has chat list, etc.)
				// Survey sidebar should not be present
				const surveySidebar = $body.find('#survey-sidebar-nav, [id*="survey-sidebar"]');
				expect(surveySidebar.length).to.equal(0);
			});
		});
	});

	context('Main View Button in Survey', () => {
		it('should show Main View button in user menu when on survey page', () => {
			// Navigate to exit-survey page
			cy.visit('/exit-survey', { failOnStatusCode: false });
			cy.wait(2000);
			
			// Click on the user menu
			cy.get('img[aria-label*="User Profile"], img[aria-label*="User Menu"]').first().click();
			cy.wait(500);
			
			// Verify Main View button exists
			cy.contains('Main View', { timeout: 10000 }).should('be.visible');
			
			// Survey View button should not be visible when on survey page
			cy.get('body').then(($body) => {
				const surveyViewButtons = $body.find('*:contains("Survey View")');
				// Main View should be shown instead
				expect(surveyViewButtons.length).to.equal(0);
			});
		});

		it('should show Survey View button in user menu when NOT on survey page', () => {
			// Navigate to a regular page
			cy.visit('/', { failOnStatusCode: false });
			cy.wait(2000);
			
			// Click on the user menu
			cy.get('img[aria-label*="User Profile"], img[aria-label*="User Menu"]').first().click();
			cy.wait(500);
			
			// Verify Survey View button exists
			cy.contains('Survey View', { timeout: 10000 }).should('be.visible');
			
			// Main View button should not be visible when not on survey page
			cy.get('body').then(($body) => {
				const mainViewButtons = $body.find('*:contains("Main View")');
				expect(mainViewButtons.length).to.equal(0);
			});
		});

		it('should navigate to main chat page when clicking Main View button', () => {
			// Navigate to exit-survey page
			cy.visit('/exit-survey', { failOnStatusCode: false });
			cy.wait(2000);
			
			// Click on the user menu
			cy.get('img[aria-label*="User Profile"], img[aria-label*="User Menu"]').first().click();
			cy.wait(500);
			
			// Click on Main View button
			cy.contains('Main View').click({ force: true });
			cy.wait(2000);
			
			// Should navigate away from exit-survey
			cy.url({ timeout: 10000 }).should('not.include', '/exit-survey');
			
			// Should be on main chat page (either / or /c/[id])
			cy.url().then((url) => {
				expect(url).to.satisfy((u: string) => {
					return u === Cypress.config().baseUrl + '/' || u.includes('/c/');
				});
			});
		});
	});
});
