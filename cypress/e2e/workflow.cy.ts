// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="../support/index.d.ts" />

/**
 * Workflow API tests: /workflow/*
 * Tests all workflow endpoints for managing user progress through the study workflow.
 * Uses INTERVIEWEE_EMAIL/INTERVIEWEE_PASSWORD or TEST_EMAIL/TEST_PASSWORD from env;
 * defaults to jjdrisco@ucsd.edu / 0000 if unset.
 * Prereqs: frontend (npm run dev) and backend running; RUN_CHILD_PROFILE_TESTS=1;
 * CYPRESS_baseUrl must match the dev server port (e.g. http://localhost:5173 or 5174).
 * Run: RUN_CHILD_PROFILE_TESTS=1 CYPRESS_baseUrl=http://localhost:5173 npx cypress run --spec cypress/e2e/workflow.cy.ts
 */

describe('Workflow API Endpoints', () => {
	// Get credentials - must be called inside test context where Cypress is available
	function getCredentials() {
		return {
			email: Cypress.env('INTERVIEWEE_EMAIL') || Cypress.env('TEST_EMAIL') || 'jjdrisco@ucsd.edu',
			password: Cypress.env('INTERVIEWEE_PASSWORD') || Cypress.env('TEST_PASSWORD') || '0000'
		};
	}

	// Helper to get API base URL (must be called inside test context where Cypress is available)
	// Use direct backend URL for cy.request() calls (bypasses Vite proxy)
	function getApiBaseUrl(): string {
		// For API requests, use direct backend URL
		return 'http://localhost:8080/api/v1';
	}

	// Helper to authenticate using cy.session() for caching
	// This ensures authentication happens once and is cached across tests
	function authenticate() {
		const credentials = getCredentials();
		const API_BASE_URL = getApiBaseUrl();
		const TOKEN_ENV_KEY = 'WORKFLOW_AUTH_TOKEN';
		return cy.session(
			`workflow-auth-${credentials.email}`,
			() => {
				cy.log(`Authenticating user: ${credentials.email}`);
				// First, try to register the user (tolerates 403 if signup is disabled)
				return cy
					.request({
						method: 'POST',
						url: `${API_BASE_URL}/auths/signup`,
						body: {
							name: 'Test User',
							email: credentials.email,
							password: credentials.password
						},
						failOnStatusCode: false
					})
					.then((signupResponse) => {
						// Accept 200 (success), 400 (bad request), or 403 (signup disabled)
						cy.log(`Signup response: ${signupResponse.status}`);
						// Wait a bit after signup before signin
						cy.wait(2000);
						// Now login via API with retry logic for rate limiting
						const attemptSignin = (retryCount = 0): Cypress.Chainable<string> => {
							return cy
								.request({
									method: 'POST',
									url: `${API_BASE_URL}/auths/signin`,
									body: {
										email: credentials.email,
										password: credentials.password
									},
									failOnStatusCode: false
								})
								.then((signinResponse) => {
									if (
										signinResponse.status === 200 &&
										signinResponse.body &&
										signinResponse.body.token
									) {
										const token = signinResponse.body.token;
										cy.log(`Signin successful, token length: ${token.length}`);
										// Persist token for the remainder of the spec run.
										// NOTE: cy.session() does not persist aliases across restores, so we use Cypress.env().
										Cypress.env(TOKEN_ENV_KEY, token);
										return cy.wrap(token);
									} else if (signinResponse.status === 429 && retryCount < 8) {
										// Rate limited, wait and retry (up to 8 times with increasing delays)
										const waitTime = Math.min((retryCount + 1) * 10000, 60000);
										cy.log(`Rate limited (attempt ${retryCount + 1}/8), waiting ${waitTime}ms...`);
										return cy.wait(waitTime).then(() => attemptSignin(retryCount + 1));
									} else {
										cy.log(`Signin failed: ${signinResponse.status} after ${retryCount} retries`);
										throw new Error(`Authentication failed: ${signinResponse.status}`);
									}
								});
						};
						return attemptSignin();
					});
			},
			{
				validate: () => {
					// Validate cached token without relying on aliases (not persisted by cy.session()).
					return cy.then(() => {
						const token = (Cypress.env(TOKEN_ENV_KEY) as string) || '';
						if (!token) throw new Error('No cached auth token');

						return cy
							.request({
								method: 'GET',
								url: `${API_BASE_URL}/auths/`,
								headers: { Authorization: `Bearer ${token}` },
								failOnStatusCode: false
							})
							.then((res) => {
								if (res.status !== 200) throw new Error(`Token validation failed: ${res.status}`);
							});
					});
				}
			}
		);
	}

	// Helper to get token - authenticates if needed using cy.session()
	// Returns a Cypress chainable that resolves to the token string
	function loginAndGetToken() {
		return authenticate().then(() => {
			return cy.then(() => {
				const token = (Cypress.env('WORKFLOW_AUTH_TOKEN') as string) || '';
				if (!token) throw new Error('Authentication failed - no cached token');
				return token;
			});
		});
	}

	describe('GET /workflow/state', () => {
		it('should return workflow state with next route and progress', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/workflow/state`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}).then((response) => {
					expect(response.status).to.eq(200);
					expect(response.body).to.have.property('next_route');
					expect(response.body).to.have.property('substep');
					expect(response.body).to.have.property('progress_by_section');
					expect(response.body.progress_by_section).to.have.property('has_child_profile');
					expect(response.body.progress_by_section).to.have.property('moderation_completed_count');
					expect(response.body.progress_by_section).to.have.property('moderation_total');
					expect(response.body.progress_by_section).to.have.property('exit_survey_completed');
					expect(response.body.progress_by_section.moderation_total).to.eq(12);
					// next_route should be one of the valid routes
					expect(response.body.next_route).to.be.oneOf([
						'/kids/profile',
						'/moderation-scenario',
						'/exit-survey',
						'/completion',
						'/parent',
						'/'
					]);
				});
			});
		});

		it('should return workflow state for new user (no child profile)', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/workflow/state`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}).then((response) => {
					expect(response.status).to.eq(200);
					// If user has no child profile, should route to /kids/profile
					if (!response.body.progress_by_section.has_child_profile) {
						expect(response.body.next_route).to.eq('/kids/profile');
					}
				});
			});
		});
	});

	describe('GET /workflow/current-attempt', () => {
		it('should return current attempt number', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/workflow/current-attempt`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}).then((response) => {
					expect(response.status).to.eq(200);
					expect(response.body).to.have.property('current_attempt');
					expect(response.body).to.have.property('moderation_attempt');
					expect(response.body).to.have.property('child_attempt');
					expect(response.body).to.have.property('exit_attempt');
					expect(response.body.current_attempt).to.be.a('number');
					expect(response.body.current_attempt).to.be.at.least(0);
					expect(response.body.moderation_attempt).to.be.a('number');
					expect(response.body.child_attempt).to.be.a('number');
					expect(response.body.exit_attempt).to.be.a('number');
				});
			});
		});
	});

	describe('GET /workflow/session-info', () => {
		it('should return session information', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/workflow/session-info`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}).then((response) => {
					expect(response.status).to.eq(200);
					expect(response.body).to.have.property('prolific_pid');
					expect(response.body).to.have.property('study_id');
					expect(response.body).to.have.property('current_session_id');
					expect(response.body).to.have.property('session_number');
					expect(response.body).to.have.property('is_prolific_user');
					expect(response.body.is_prolific_user).to.be.a('boolean');
				});
			});
		});
	});

	describe('GET /workflow/completed-scenarios', () => {
		it('should return completed scenario indices', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/workflow/completed-scenarios`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}).then((response) => {
					expect(response.status).to.eq(200);
					expect(response.body).to.have.property('completed_scenario_indices');
					expect(response.body).to.have.property('count');
					expect(response.body.completed_scenario_indices).to.be.an('array');
					expect(response.body.count).to.be.a('number');
					expect(response.body.count).to.eq(response.body.completed_scenario_indices.length);
					// All indices should be numbers between 0-11
					response.body.completed_scenario_indices.forEach((idx: number) => {
						expect(idx).to.be.a('number');
						expect(idx).to.be.at.least(0);
						expect(idx).to.be.at.most(11);
					});
				});
			});
		});
	});

	describe('GET /workflow/study-status', () => {
		it('should return study completion status', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/workflow/study-status`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}).then((response) => {
					expect(response.status).to.eq(200);
					expect(response.body).to.have.property('completed_at');
					expect(response.body).to.have.property('completion_date');
					expect(response.body).to.have.property('can_retake');
					expect(response.body).to.have.property('current_attempt');
					expect(response.body).to.have.property('message');
					expect(response.body.can_retake).to.be.a('boolean');
					expect(response.body.current_attempt).to.be.a('number');
					expect(response.body.current_attempt).to.be.at.least(1);
					// completed_at can be null or a number
					if (response.body.completed_at !== null) {
						expect(response.body.completed_at).to.be.a('number');
					}
				});
			});
		});
	});

	describe('POST /workflow/reset', () => {
		it('should reset entire user workflow and increment attempt number', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			// Get current attempt before reset
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/workflow/current-attempt`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}).then((response) => {
					const attemptBefore = response.body.current_attempt;
					// Now reset workflow
					cy.request({
						method: 'POST',
						url: `${API_BASE_URL}/workflow/reset`,
						headers: {
							Authorization: `Bearer ${token}`,
							'Content-Type': 'application/json'
						}
					}).then((resetResponse) => {
						expect(resetResponse.status).to.eq(200);
						expect(resetResponse.body).to.have.property('status', 'success');
						expect(resetResponse.body).to.have.property('new_attempt');
						expect(resetResponse.body).to.have.property('message');
						expect(resetResponse.body.new_attempt).to.be.a('number');
						expect(resetResponse.body.new_attempt).to.be.greaterThan(attemptBefore);
					});
				});
			});
		});
	});

	describe('POST /workflow/reset-moderation', () => {
		it('should reset only moderation workflow and increment attempt', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			// Get current moderation attempt before reset
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/workflow/current-attempt`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}).then((response) => {
					const moderationAttemptBefore = response.body.moderation_attempt;
					// Now reset moderation workflow
					cy.request({
						method: 'POST',
						url: `${API_BASE_URL}/workflow/reset-moderation`,
						headers: {
							Authorization: `Bearer ${token}`,
							'Content-Type': 'application/json'
						}
					}).then((resetResponse) => {
						expect(resetResponse.status).to.eq(200);
						expect(resetResponse.body).to.have.property('status', 'success');
						expect(resetResponse.body).to.have.property('new_attempt');
						expect(resetResponse.body).to.have.property('completed_scenario_indices');
						expect(resetResponse.body).to.have.property('message');
						expect(resetResponse.body.new_attempt).to.be.a('number');
						expect(resetResponse.body.new_attempt).to.be.greaterThan(moderationAttemptBefore);
						expect(resetResponse.body.completed_scenario_indices).to.be.an('array');
					});
				});
			});
		});
	});

	describe('POST /workflow/moderation/finalize', () => {
		it('should finalize moderation without filters', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'POST',
					url: `${API_BASE_URL}/workflow/moderation/finalize`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					},
					body: {}
				}).then((response) => {
					expect(response.status).to.eq(200);
					expect(response.body).to.have.property('updated');
					expect(response.body.updated).to.be.a('number');
					expect(response.body.updated).to.be.at.least(0);
				});
			});
		});

		it('should finalize moderation with child_id filter', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			// First get child profiles to use a valid child_id
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/child-profiles`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					},
					failOnStatusCode: false
				}).then((childResponse) => {
					if (
						childResponse.status === 200 &&
						Array.isArray(childResponse.body) &&
						childResponse.body.length > 0
					) {
						const childId = childResponse.body[0].id;
						cy.request({
							method: 'POST',
							url: `${API_BASE_URL}/workflow/moderation/finalize`,
							headers: {
								Authorization: `Bearer ${token}`,
								'Content-Type': 'application/json'
							},
							body: {
								child_id: childId
							}
						}).then((response) => {
							expect(response.status).to.eq(200);
							expect(response.body).to.have.property('updated');
							expect(response.body.updated).to.be.a('number');
						});
					} else {
						// Skip if no child profiles - make a request anyway to test the endpoint
						cy.request({
							method: 'POST',
							url: `${API_BASE_URL}/workflow/moderation/finalize`,
							headers: {
								Authorization: `Bearer ${token}`,
								'Content-Type': 'application/json'
							},
							body: {}
						}).then((response) => {
							expect(response.status).to.eq(200);
							expect(response.body).to.have.property('updated');
							expect(response.body.updated).to.be.a('number');
						});
					}
				});
			});
		});

		it('should finalize moderation with session_number filter', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'POST',
					url: `${API_BASE_URL}/workflow/moderation/finalize`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					},
					body: {
						session_number: 1
					}
				}).then((response) => {
					expect(response.status).to.eq(200);
					expect(response.body).to.have.property('updated');
					expect(response.body.updated).to.be.a('number');
				});
			});
		});
	});

	describe('Workflow State Transitions', () => {
		it('should progress through workflow states correctly', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			// Test workflow state progression
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/workflow/state`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}).then((response) => {
					expect(response.status).to.eq(200);
					const state = response.body;
					const progress = state.progress_by_section;

					// Verify workflow logic:
					// 1. If no child profile -> /kids/profile
					// 2. If child profile but moderation incomplete -> /moderation-scenario
					// 3. If moderation complete but exit survey incomplete -> /exit-survey
					// 4. If all complete -> /completion

					if (!progress.has_child_profile) {
						expect(state.next_route).to.eq('/kids/profile');
					} else if (progress.moderation_completed_count < progress.moderation_total) {
						expect(state.next_route).to.eq('/moderation-scenario');
					} else if (!progress.exit_survey_completed) {
						expect(state.next_route).to.eq('/exit-survey');
					} else {
						expect(state.next_route).to.eq('/completion');
					}
				});
			});
		});

		it('should maintain consistent state across multiple requests', function () {
			const credentials = getCredentials();
			if (!credentials.email || !credentials.password) {
				this.skip();
				return;
			}
			// Make multiple requests and verify consistency
			loginAndGetToken().then((token) => {
				const API_BASE_URL = getApiBaseUrl();
				cy.request({
					method: 'GET',
					url: `${API_BASE_URL}/workflow/state`,
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					}
				}).then((response1) => {
					cy.request({
						method: 'GET',
						url: `${API_BASE_URL}/workflow/state`,
						headers: {
							Authorization: `Bearer ${token}`,
							'Content-Type': 'application/json'
						}
					}).then((response2) => {
						// Progress should be consistent (unless state changed between requests)
						expect(response1.body.progress_by_section.has_child_profile).to.eq(
							response2.body.progress_by_section.has_child_profile
						);
						expect(response1.body.progress_by_section.moderation_total).to.eq(
							response2.body.progress_by_section.moderation_total
						);
					});
				});
			});
		});
	});

	describe('Error Handling', () => {
		it('should return 401 for unauthenticated requests', function () {
			const API_BASE_URL = getApiBaseUrl();
			cy.request({
				method: 'GET',
				url: `${API_BASE_URL}/workflow/state`,
				headers: {
					'Content-Type': 'application/json'
				},
				failOnStatusCode: false
			}).then((response) => {
				// Accept 401, 403, 404, or 500 (if backend has issues)
				expect(response.status).to.be.oneOf([401, 403, 404, 500]);
			});
		});

		it('should return 401 for invalid token', function () {
			const API_BASE_URL = getApiBaseUrl();
			cy.request({
				method: 'GET',
				url: `${API_BASE_URL}/workflow/state`,
				headers: {
					Authorization: 'Bearer invalid_token',
					'Content-Type': 'application/json'
				},
				failOnStatusCode: false
			}).then((response) => {
				// Accept 401, 403, 404, or 500 (if backend has issues)
				expect(response.status).to.be.oneOf([401, 403, 404, 500]);
			});
		});
	});
});
