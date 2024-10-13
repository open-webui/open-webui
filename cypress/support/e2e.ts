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
			// Visit auth page
			cy.visit('/auth');
			// Fill out the form
			cy.get('input[autocomplete="email"]').type(email);
			cy.get('input[type="password"]').type(password);
			// Submit the form
			cy.get('button[type="submit"]').click();
			// Wait until the user is redirected to the home page
			cy.get('#chat-search').should('exist');
			// Get the current version to skip the changelog dialog
			if (localStorage.getItem('version') === null) {
				cy.get('button').contains("Okay, Let's Go!").click();
			}
		},
		{
			validate: () => {
				cy.request({
					method: 'GET',
					url: '/api/v1/auths/',
					headers: {
						Authorization: 'Bearer ' + localStorage.getItem('token')
					}
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
			expect(response.status).to.be.oneOf([200, 400]);
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

Cypress.Commands.add('uploadTestDocument', (suffix: any) => {
	// Login as admin
	cy.loginAdmin();
	// upload example document
	cy.visit('/workspace/documents');
	// Create a document
	cy.get("button[aria-label='Add Docs']").click();
	cy.readFile('cypress/data/example-doc.txt').then((text) => {
		// select file
		cy.get('#upload-doc-input').selectFile(
			{
				contents: Cypress.Buffer.from(text + Date.now()),
				fileName: `document-test-initial-${suffix}.txt`,
				mimeType: 'text/plain',
				lastModified: Date.now()
			},
			{
				force: true
			}
		);
		// open tag input
		cy.get("button[aria-label='Add Tag']").click();
		cy.get("input[placeholder='Add a tag']").type('cypress-test');
		cy.get("button[aria-label='Save Tag']").click();

		// submit to upload
		cy.get("button[type='submit']").click();

		// wait for upload to finish
		cy.get('button').contains('#cypress-test').should('exist');
		cy.get('div').contains(`document-test-initial-${suffix}.txt`).should('exist');
	});
});

Cypress.Commands.add('deleteTestDocument', (suffix: any) => {
	cy.loginAdmin();
	cy.visit('/workspace/documents');
	// clean up uploaded documents
	cy.get('div')
		.contains(`document-test-initial-${suffix}.txt`)
		.find("button[aria-label='Delete Doc']")
		.click();
});

before(() => {
	cy.registerAdmin();
});
