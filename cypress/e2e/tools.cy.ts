// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

// These tests run through the chat flow.
describe('Settings', () => {
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

    it('user can add tool', () => {
      // Click on the add tool button
      cy.visit("/workspace/tools/create")

      // TODO: better way to get these!
      cy.get('input[placeholder="Toolkit Name (e.g. My ToolKit)"]')
        .type('My Custom Toolkit Name');

      cy.get('input[placeholder="Toolkit ID (e.g. my_toolkit)"]')
        .type('my_custom_toolkit');

      cy.get('input[placeholder="Toolkit Description (e.g. A toolkit for performing various operations)"]')
        .type('This is a custom toolkit for various operations.');

      cy.contains('button', 'Save').click();
      cy.contains('button', 'Confirm').click();
    });

    it('user can chat using tool', () => {
      cy.visit("/");

      // Open the tools menu
      cy.get('div[aria-label="More"]')
        .find('button')
        .click({ force: true });

      // TODO: better way to get this!
      cy.get('div.max-h-28.overflow-y-auto.scrollbar-hidden')  // Select the container div
        .find('div.flex').first().find('button').click();  // Enable first tool

      // Click on the model selector
      cy.get('button[aria-label="Select a model"]').click();
      // Select the first model
      cy.get('button[aria-label="model-item"]').first().click();
      // Type a message
      cy.get('#chat-textarea').type('What\'s 12786/9487+897/900? Make sure you answer with at least 5 digits after the decimal.', {
        force: true
      });
      // Send the message
      cy.get('button[type="submit"]').click();
      // User's message should be visible
      cy.get('.chat-user').should('exist');
      // Wait for the response
      // .chat-assistant is created after the first token is received
      cy.get('.chat-assistant', { timeout: 10_000 }).should('exist');
      // Generation should contain the answer from calculator tool
      cy.get('.chat-assistant', { timeout: 10_000 }).should('contain.text', '2.3444');
      // Generation Info is created after the stop token is received
      cy.get('div[aria-label="Generation Info"]', { timeout: 120_000 }).should('exist');
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
      // .chat-assistant is created after the first token is received
      cy.get('.chat-assistant', { timeout: 10_000 }).should('exist');
      // Generation Info is created after the stop token is received
      cy.get('div[aria-label="Generation Info"]', { timeout: 120_000 }).should('exist');
    });
  });
});
