import { describe, it, expect, beforeEach, vi } from 'vitest';
import { PiiSessionManager, type ExtendedPiiEntity } from './pii';

describe('PII Session Manager', () => {
	let piiManager: PiiSessionManager;

	beforeEach(() => {
		// Mock window object for Node.js test environment
		Object.defineProperty(global, 'window', {
			value: {
				triggerPiiChatSave: vi.fn().mockResolvedValue(undefined)
			},
			writable: true
		});

		// Reset singleton instance for each test
		PiiSessionManager.resetInstance();
		piiManager = PiiSessionManager.getInstance();
	});

	describe('Entity Consolidation - with conversation id', () => {
		it('should consolidate entities with same text but different IDs', () => {
			const conversationId = 'test-conversation-same-text-different-ids';

			// First, set up existing entities
			const existingEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				}
			];

			piiManager.setConversationEntitiesFromLatestDetection(conversationId, existingEntities);

			// Now add new entities with different ID
			const newEntities: ExtendedPiiEntity[] = [
				{
					id: 999, // Different ID
					label: 'PERSON_999', // Should consolidate
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 20, end_idx: 28 }], // Different position
					shouldMask: true
				}
			];

			// This should consolidate by label, not by ID
			piiManager.setConversationEntitiesFromLatestDetection(conversationId, newEntities);

			const result = piiManager.getEntitiesForDisplay(conversationId);

			// Should have only one entity (consolidated)
			expect(result).toHaveLength(1);
			expect(result[0].label).toBe('PERSON_1');
			expect(result[0].id).toBe(1); // Should keep original ID
			expect(result[0].shouldMask).toBe(true); // Should preserve original masking state
			expect(result[0].occurrences).toHaveLength(2); // Should merge occurrences
			expect(result[0].occurrences[0]).toEqual({ start_idx: 0, end_idx: 8 });
			expect(result[0].occurrences[1]).toEqual({ start_idx: 20, end_idx: 28 });
		});

		it('should handle case-insensitive matching', () => {
			const conversationId = 'test-conversation-case-insensitive';
			const existingEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				}
			];

			piiManager.setConversationEntitiesFromLatestDetection(conversationId, existingEntities);

			const newEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'JOHN DOE',
					text: 'john doe',
					occurrences: [{ start_idx: 10, end_idx: 18 }],
					shouldMask: true
				}
			];

			// This should consolidate by label, not by ID
			piiManager.setConversationEntitiesFromLatestDetection(conversationId, newEntities);

			const result = piiManager.getEntitiesForDisplay(conversationId);

			expect(result).toHaveLength(1);
			expect(result[0].id).toBe(1);
			expect(result[0].label).toBe('PERSON_1');
			expect(result[0].raw_text).toBe('John Doe');
			expect(result[0].text).toBe('john doe');
			expect(result[0].shouldMask).toBe(true);
			expect(result[0].occurrences).toHaveLength(2);
			expect(result[0].occurrences[0]).toEqual({ start_idx: 0, end_idx: 8 });
			expect(result[0].occurrences[1]).toEqual({ start_idx: 10, end_idx: 18 });
		});

		it('should handle masking state', () => {
			const conversationId = 'test-conversation-case-masking';
			const existingEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: false
				},
				{
					id: 2,
					label: 'EMAIL_2',
					type: 'EMAIL',
					raw_text: 'john@example.com',
					text: 'john@example.com',
					occurrences: [{ start_idx: 10, end_idx: 25 }],
					shouldMask: true
				}
			];

			piiManager.setConversationEntitiesFromLatestDetection(conversationId, existingEntities);

			const newEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 10, end_idx: 18 }],
					shouldMask: true
				},
				{
					id: 2,
					label: 'EMAIL_2',
					type: 'EMAIL',
					raw_text: 'john@example.com',
					text: 'john@example.com',
					occurrences: [{ start_idx: 20, end_idx: 35 }],
					shouldMask: false
				}
			];

			// This should consolidate by label, not by ID
			piiManager.setConversationEntitiesFromLatestDetection(conversationId, newEntities);

			const result = piiManager.getEntitiesForDisplay(conversationId);

			expect(result).toHaveLength(2);
			expect(result[0].id).toBe(1);
			expect(result[0].label).toBe('PERSON_1');
			expect(result[0].shouldMask).toBe(false);
			expect(result[0].occurrences).toHaveLength(2);
			expect(result[1].id).toBe(2);
			expect(result[1].label).toBe('EMAIL_2');
			expect(result[1].shouldMask).toBe(true);
			expect(result[1].occurrences).toHaveLength(2);
		});

		it('should handle entities without matches', () => {
			const conversationId = 'test-conversation-without-matches';
			const existingEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				}
			];

			piiManager.setConversationEntitiesFromLatestDetection(conversationId, existingEntities);

			const newEntities: ExtendedPiiEntity[] = [
				{
					id: 2,
					label: 'PERSON_2',
					type: 'PERSON',
					raw_text: 'Jane Smith',
					text: 'jane smith',
					occurrences: [{ start_idx: 0, end_idx: 10 }],
					shouldMask: true
				}
			];

			// This should consolidate by label, not by ID
			piiManager.setConversationEntitiesFromLatestDetection(conversationId, newEntities);

			const result = piiManager.getEntitiesForDisplay(conversationId);

			expect(result).toHaveLength(2);
			expect(result[0].id).toBe(1);
			expect(result[0].label).toBe('PERSON_1');
			expect(result[0].raw_text).toBe('John Doe');
			expect(result[0].text).toBe('john doe');
			expect(result[0].shouldMask).toBe(true);
			expect(result[0].occurrences).toHaveLength(1);
			expect(result[0].occurrences[0]).toEqual({ start_idx: 0, end_idx: 8 });
			expect(result[1].id).toBe(2);
			expect(result[1].label).toBe('PERSON_2');
			expect(result[1].raw_text).toBe('Jane Smith');
			expect(result[1].text).toBe('jane smith');
			expect(result[1].shouldMask).toBe(true);
			expect(result[1].occurrences).toHaveLength(1);
			expect(result[1].occurrences[0]).toEqual({ start_idx: 0, end_idx: 10 });
		});
	});

	describe('Entity Consolidation - without conversation id', () => {
		it('should consolidate entities with same text but different IDs', () => {
			piiManager.activateTemporaryState();
			// First, set up existing entities
			const existingEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				}
			];

			piiManager.setTemporaryStateEntities(existingEntities);

			// Now add new entities with different ID
			const newEntities: ExtendedPiiEntity[] = [
				{
					id: 999, // Different ID
					label: 'PERSON_999', // Should consolidate
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 20, end_idx: 28 }], // Different position
					shouldMask: true
				}
			];

			// This should consolidate by text
			piiManager.setTemporaryStateEntities(newEntities);

			const result = piiManager.getEntitiesForDisplay();

			// Should have only one entity (consolidated)
			expect(result).toHaveLength(1);
			expect(result[0].label).toBe('PERSON_1');
			expect(result[0].id).toBe(1); // Should keep original ID
			expect(result[0].shouldMask).toBe(true); // Should preserve original masking state
			expect(result[0].occurrences).toHaveLength(2); // Should merge occurrences
			expect(result[0].occurrences[0]).toEqual({ start_idx: 0, end_idx: 8 });
			expect(result[0].occurrences[1]).toEqual({ start_idx: 20, end_idx: 28 });
		});

		it('should handle case-insensitive matching', () => {
			piiManager.activateTemporaryState();
			const existingEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				}
			];

			piiManager.setTemporaryStateEntities(existingEntities);

			const newEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'JOHN DOE',
					text: 'john doe',
					occurrences: [{ start_idx: 10, end_idx: 18 }],
					shouldMask: true
				}
			];

			// This should consolidate by label, not by ID
			piiManager.setTemporaryStateEntities(newEntities);

			const result = piiManager.getEntitiesForDisplay();

			expect(result).toHaveLength(1);
			expect(result[0].id).toBe(1);
			expect(result[0].label).toBe('PERSON_1');
			expect(result[0].raw_text).toBe('John Doe');
			expect(result[0].text).toBe('john doe');
			expect(result[0].shouldMask).toBe(true);
			expect(result[0].occurrences).toHaveLength(2);
			expect(result[0].occurrences[0]).toEqual({ start_idx: 0, end_idx: 8 });
			expect(result[0].occurrences[1]).toEqual({ start_idx: 10, end_idx: 18 });
		});

		it('should handle masking state', () => {
			piiManager.activateTemporaryState();
			const existingEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: false
				},
				{
					id: 2,
					label: 'EMAIL_2',
					type: 'EMAIL',
					raw_text: 'john@example.com',
					text: 'john@example.com',
					occurrences: [{ start_idx: 10, end_idx: 25 }],
					shouldMask: true
				}
			];

			piiManager.setTemporaryStateEntities(existingEntities);

			const newEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 10, end_idx: 18 }],
					shouldMask: true
				},
				{
					id: 2,
					label: 'EMAIL_2',
					type: 'EMAIL',
					raw_text: 'john@example.com',
					text: 'john@example.com',
					occurrences: [{ start_idx: 20, end_idx: 35 }],
					shouldMask: false
				}
			];

			// This should consolidate by label, not by ID
			piiManager.setTemporaryStateEntities(newEntities);

			const result = piiManager.getEntitiesForDisplay();

			expect(result).toHaveLength(2);
			expect(result[0].id).toBe(1);
			expect(result[0].label).toBe('PERSON_1');
			expect(result[0].shouldMask).toBe(false);
			expect(result[0].occurrences).toHaveLength(2);
			expect(result[1].id).toBe(2);
			expect(result[1].label).toBe('EMAIL_2');
			expect(result[1].shouldMask).toBe(true);
			expect(result[1].occurrences).toHaveLength(2);
		});

		it('should handle entities without matches', () => {
			piiManager.activateTemporaryState();
			const existingEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				}
			];

			piiManager.setTemporaryStateEntities(existingEntities);

			const newEntities: ExtendedPiiEntity[] = [
				{
					id: 2,
					label: 'PERSON_2',
					type: 'PERSON',
					raw_text: 'Jane Smith',
					text: 'jane smith',
					occurrences: [{ start_idx: 0, end_idx: 10 }],
					shouldMask: true
				}
			];

			// This should consolidate by label, not by ID
			piiManager.setTemporaryStateEntities(newEntities);

			const result = piiManager.getEntitiesForDisplay();

			expect(result).toHaveLength(2);
			expect(result[0].id).toBe(1);
			expect(result[0].label).toBe('PERSON_1');
			expect(result[0].raw_text).toBe('John Doe');
			expect(result[0].text).toBe('john doe');
			expect(result[0].shouldMask).toBe(true);
			expect(result[0].occurrences).toHaveLength(1);
			expect(result[0].occurrences[0]).toEqual({ start_idx: 0, end_idx: 8 });
			expect(result[1].id).toBe(2);
			expect(result[1].label).toBe('PERSON_2');
			expect(result[1].raw_text).toBe('Jane Smith');
			expect(result[1].text).toBe('jane smith');
			expect(result[1].shouldMask).toBe(true);
			expect(result[1].occurrences).toHaveLength(1);
			expect(result[1].occurrences[0]).toEqual({ start_idx: 0, end_idx: 10 });
		});
	});

	describe('Session Management', () => {
		it('should retrieve conversation entities correctly', () => {
			const conversationId = 'test-conversation-retrieval';
			const entities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				},
				{
					id: 2,
					label: 'EMAIL_2',
					type: 'EMAIL',
					raw_text: 'john@example.com',
					text: 'john@example.com',
					occurrences: [{ start_idx: 10, end_idx: 25 }],
					shouldMask: false
				}
			];

			piiManager.setConversationEntitiesFromLatestDetection(conversationId, entities);
			const retrieved = piiManager.getEntitiesForDisplay(conversationId);

			expect(retrieved).toHaveLength(2);
			expect(retrieved[0].label).toBe('PERSON_1');
			expect(retrieved[0].shouldMask).toBe(true);
			expect(retrieved[0].occurrences).toHaveLength(1);
			expect(retrieved[0].occurrences[0]).toEqual({ start_idx: 0, end_idx: 8 });
			expect(retrieved[1].label).toBe('EMAIL_2');
			expect(retrieved[1].shouldMask).toBe(false);
			expect(retrieved[1].occurrences).toHaveLength(1);
			expect(retrieved[1].occurrences[0]).toEqual({ start_idx: 10, end_idx: 25 });
		});

		it('should merge entities with existing ones', () => {
			const conversationId = 'test-conversation-merge';
			const initialEntities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				}
			];

			piiManager.setConversationEntitiesFromLatestDetection(conversationId, initialEntities);

			const newEntities: ExtendedPiiEntity[] = [
				{
					id: 2,
					label: 'EMAIL_2',
					type: 'EMAIL',
					raw_text: 'john@example.com',
					text: 'john@example.com',
					occurrences: [{ start_idx: 10, end_idx: 25 }],
					shouldMask: false
				}
			];

			piiManager.setConversationEntitiesFromLatestDetection(conversationId, newEntities);
			const retrieved = piiManager.getEntitiesForDisplay(conversationId);

			expect(retrieved).toHaveLength(2);
			expect(retrieved.find((e) => e.label === 'PERSON_1')?.shouldMask).toBe(true);
			expect(retrieved.find((e) => e.label === 'EMAIL_2')?.shouldMask).toBe(false);
		});

		it('should convert entities to API format correctly', () => {
			const conversationId = 'test-conversation-api-format';
			const entities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				}
			];

			piiManager.setConversationEntitiesFromLatestDetection(conversationId, entities);
			const apiFormat = piiManager.getKnownEntitiesForApi(conversationId);

			expect(apiFormat).toHaveLength(1);
			expect(apiFormat[0]).toEqual({
				id: 1,
				label: 'PERSON_1',
				name: 'john doe',
				shouldMask: true
			});
		});
	});

	describe('Temporary State Management', () => {
		it('should handle temporary state for new chats', () => {
			piiManager.activateTemporaryState();

			const entities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: false
				},
				{
					id: 2,
					label: 'EMAIL_2',
					type: 'EMAIL',
					raw_text: 'john@example.com',
					text: 'john@example.com',
					occurrences: [{ start_idx: 10, end_idx: 25 }],
					shouldMask: true
				}
			];

			piiManager.setTemporaryStateEntities(entities);
			const retrieved = piiManager.getEntitiesForDisplay();

			expect(retrieved).toHaveLength(2);
			expect(retrieved[0].label).toBe('PERSON_1');
			expect(retrieved[0].shouldMask).toBe(false);
			expect(retrieved[1].label).toBe('EMAIL_2');
			expect(retrieved[1].shouldMask).toBe(true);
			expect(retrieved[0].occurrences).toHaveLength(1);
			expect(retrieved[0].occurrences[0]).toEqual({ start_idx: 0, end_idx: 8 });
			expect(retrieved[1].occurrences).toHaveLength(1);
			expect(retrieved[1].occurrences[0]).toEqual({ start_idx: 10, end_idx: 25 });
		});

		it('should transfer temporary state to conversation', () => {
			piiManager.activateTemporaryState();

			const entities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				},
				{
					id: 2,
					label: 'EMAIL_2',
					type: 'EMAIL',
					raw_text: 'john@example.com',
					text: 'john@example.com',
					occurrences: [{ start_idx: 10, end_idx: 25 }],
					shouldMask: false
				}
			];

			piiManager.setTemporaryStateEntities(entities);

			const conversationId = 'new-conversation-transfer';
			piiManager.transferTemporaryToConversation(conversationId);

			const retrieved = piiManager.getEntitiesForDisplay(conversationId);
			expect(retrieved).toHaveLength(2);
			expect(retrieved[0].label).toBe('PERSON_1');
			expect(retrieved[0].shouldMask).toBe(true);
			expect(retrieved[0].occurrences).toHaveLength(1);
			expect(retrieved[0].occurrences[0]).toEqual({ start_idx: 0, end_idx: 8 });
			expect(retrieved[1].label).toBe('EMAIL_2');
			expect(retrieved[1].shouldMask).toBe(false);
			expect(retrieved[1].occurrences).toHaveLength(1);
			expect(retrieved[1].occurrences[0]).toEqual({ start_idx: 10, end_idx: 25 });
			// Temporary state should be cleared
			expect(piiManager.isTemporaryStateActive()).toBe(false);
		});
	});

	describe('Entity Masking Toggle', () => {
		it('should toggle entity masking state', () => {
			const conversationId = 'test-conversation-toggle';
			const entities: ExtendedPiiEntity[] = [
				{
					id: 1,
					label: 'PERSON_1',
					type: 'PERSON',
					raw_text: 'John Doe',
					text: 'john doe',
					occurrences: [{ start_idx: 0, end_idx: 8 }],
					shouldMask: true
				}
			];

			piiManager.setConversationEntitiesFromLatestDetection(conversationId, entities);

			// Toggle masking
			piiManager.toggleEntityMasking('PERSON_1', 0, conversationId);

			const retrieved = piiManager.getEntitiesForDisplay(conversationId);
			expect(retrieved[0].shouldMask).toBe(false);

			// Toggle back
			piiManager.toggleEntityMasking('PERSON_1', 0, conversationId);
			const retrieved2 = piiManager.getEntitiesForDisplay(conversationId);
			expect(retrieved2[0].shouldMask).toBe(true);
		});
	});
});
