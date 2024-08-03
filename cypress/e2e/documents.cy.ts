// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

describe('Documents', () => {
	const timestamp = Date.now();

	before(() => {
		cy.uploadTestDocument(timestamp);
	});

	after(() => {
		cy.deleteTestDocument(timestamp);
	});

	context('Admin', () => {
		beforeEach(() => {
			// Login as the admin user
			cy.loginAdmin();
			// Visit the home page
			cy.visit('/workspace/documents');
			cy.get('button').contains('#cypress-test').click();
		});

		it('can see documents', () => {
			cy.get('div').contains(`document-test-initial-${timestamp}.txt`).should('have.length', 1);
		});

		it('can see edit button', () => {
			cy.get('div')
				.contains(`document-test-initial-${timestamp}.txt`)
				.get("button[aria-label='Edit Doc']")
				.should('exist');
		});

		it('can see delete button', () => {
			cy.get('div')
				.contains(`document-test-initial-${timestamp}.txt`)
				.get("button[aria-label='Delete Doc']")
				.should('exist');
		});

		it('can see upload button', () => {
			cy.get("button[aria-label='Add Docs']").should('exist');
		});
	});
});
