describe('Agent Creation Form', () => {
  const mockModels = [
    { id: 'ollama/mistral:latest', name: 'Mistral (Ollama)' },
    { id: 'gguf/phi-2:latest', name: 'Phi-2 (GGUF)' },
    { id: 'openai/gpt-4', name: 'GPT-4 (OpenAI)' },
  ];

  const agentDetails = {
    name: 'Test Agent',
    role: 'Test Role',
    systemMessage: 'This is a test system message.',
    skills: 'testing, cypress, frontend',
  };

  beforeEach(() => {
    // Mock the GET /api/models API call
    cy.intercept('GET', '/api/models', {
      statusCode: 200,
      body: { data: mockModels },
    }).as('getModels');

    // Mock the POST /api/v1/agents/ API call
    cy.intercept('POST', '/api/v1/agents/', {
      statusCode: 201, // Simulate successful creation
      body: {
        id: 1,
        user_id: 'test-user',
        timestamp: new Date().toISOString(),
        ...agentDetails,
        model_id: '', // This will be set by the selected model
      },
    }).as('createAgent');

    // Visit the agent creation page
    cy.visit('/agents/create');
    cy.wait('@getModels'); // Ensure models are loaded before interacting
  });

  it('should submit the form with the correct data including the selected model_id', () => {
    const selectedModel = mockModels[1]; // Select the GGUF model for this test

    // Fill in the form
    cy.get('#agentName').type(agentDetails.name);
    cy.get('#agentRole').type(agentDetails.role);
    cy.get('#systemMessage').type(agentDetails.systemMessage);
    cy.get('#skills').type(agentDetails.skills);

    // Select the model from the dropdown
    // The value of the option should be the model.id
    cy.get('#llmModel').select(selectedModel.id);

    // Submit the form
    cy.get('button[type="submit"]').click();

    // Wait for the createAgent API call and assert
    cy.wait('@createAgent').then((interception) => {
      expect(interception.response.statusCode).to.eq(201);
      
      const requestBody = interception.request.body;
      expect(requestBody).to.have.property('name', agentDetails.name);
      expect(requestBody).to.have.property('role', agentDetails.role);
      expect(requestBody).to.have.property('system_message', agentDetails.systemMessage);
      expect(requestBody).to.have.property('skills', agentDetails.skills);
      expect(requestBody).to.have.property('model_id', selectedModel.id);
    });

    // Also verify that a success toast message is shown (optional but good practice)
    cy.contains('Agent "Test Agent" created successfully!').should('be.visible');
  });

  // Add more tests for other models if needed
  it('should allow selecting an Ollama model', () => {
    const selectedModel = mockModels[0]; // Ollama model

    cy.get('#llmModel').select(selectedModel.id);
    cy.get('#agentName').type(agentDetails.name); // Need to fill required fields
    cy.get('#agentRole').type(agentDetails.role); // Need to fill required fields
    cy.get('button[type="submit"]').click();

    cy.wait('@createAgent').then((interception) => {
      expect(interception.request.body.model_id).to.eq(selectedModel.id);
    });
  });

  it('should allow selecting an OpenAI model', () => {
    const selectedModel = mockModels[2]; // OpenAI model

    cy.get('#llmModel').select(selectedModel.id);
    cy.get('#agentName').type(agentDetails.name); // Need to fill required fields
    cy.get('#agentRole').type(agentDetails.role); // Need to fill required fields
    cy.get('button[type="submit"]').click();

    cy.wait('@createAgent').then((interception) => {
      expect(interception.request.body.model_id).to.eq(selectedModel.id);
    });
  });
});
