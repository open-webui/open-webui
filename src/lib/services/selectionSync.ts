import { selectionsAPI, type Selection, type SelectionForm } from '$lib/apis/selections';
import { user } from '$lib/stores';
import { get } from 'svelte/store';

/**
 * Service for syncing selections between localStorage and backend database
 * 
 * This service handles:
 * 1. Syncing localStorage selections to backend when user is authenticated
 * 2. Restoring selections from backend when user logs in
 * 3. Keeping localStorage and backend in sync
 * 4. Providing fallback to localStorage when backend is unavailable
 */

class SelectionSyncService {
  private readonly STORAGE_KEY = 'saved-selections';
  private readonly SYNC_KEY = 'selections-synced';
  private isOnline = true;

  constructor() {
    // Listen for online/offline events
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        this.isOnline = true;
        this.syncToBackend();
      });
      
      window.addEventListener('offline', () => {
        this.isOnline = false;
      });
    }
  }

  /**
   * Save a selection to both localStorage and backend
   */
  async saveSelection(selection: SelectionForm): Promise<void> {
    // Always save to localStorage first (for offline support)
    this.saveToLocalStorage(selection);

    // Try to save to backend if online and user is authenticated
    if (this.isOnline && this.isUserAuthenticated()) {
      try {
        await selectionsAPI.createSelection(selection);
        console.log('Selection saved to backend:', selection);
      } catch (error) {
        console.warn('Failed to save selection to backend:', error);
        // Selection is still saved in localStorage, so user doesn't lose data
      }
    }
  }

  /**
   * Save multiple selections (for bulk sync)
   */
  async saveBulkSelections(selections: SelectionForm[]): Promise<void> {
    // Save to localStorage
    selections.forEach(selection => this.saveToLocalStorage(selection));

    // Try to save to backend
    if (this.isOnline && this.isUserAuthenticated()) {
      try {
        await selectionsAPI.createBulkSelections(selections);
        console.log(`Synced ${selections.length} selections to backend`);
      } catch (error) {
        console.warn('Failed to sync selections to backend:', error);
      }
    }
  }

  /**
   * Get selections for a specific chat
   */
  async getChatSelections(chatId: string): Promise<SelectionForm[]> {
    // Try backend first if online and authenticated
    if (this.isOnline && this.isUserAuthenticated()) {
      try {
        const backendSelections = await selectionsAPI.getChatSelections(chatId);
        // Convert backend format to local format
        return backendSelections.map(selection => ({
          chatId: selection.chat_id,
          messageId: selection.message_id,
          role: selection.role,
          text: selection.selected_text
        }));
      } catch (error) {
        console.warn('Failed to get selections from backend, falling back to localStorage:', error);
      }
    }

    // Fallback to localStorage
    return this.getFromLocalStorage(chatId);
  }

  /**
   * Sync all localStorage selections to backend
   */
  async syncToBackend(): Promise<void> {
    if (!this.isOnline || !this.isUserAuthenticated()) {
      return;
    }

    const currentUser = get(user);
    if (!currentUser) {
      return;
    }

    try {
      // Check if we've already synced
      const lastSync = localStorage.getItem(this.SYNC_KEY);
      const lastSyncTime = lastSync ? parseInt(lastSync) : 0;
      const now = Date.now();

      // Only sync if it's been more than 5 minutes since last sync
      if (now - lastSyncTime < 5 * 60 * 1000) {
        return;
      }

      // Get all selections from localStorage
      const allSelections = this.getAllFromLocalStorage();
      
      if (allSelections.length === 0) {
        return;
      }

      // Convert to backend format
      const backendSelections: SelectionForm[] = allSelections.map(selection => ({
        chat_id: selection.chatId,
        message_id: selection.messageId,
        role: selection.role,
        selected_text: selection.text,
        context: undefined, // Could be enhanced to include context
        meta: {
          synced_from: 'localStorage',
          original_timestamp: Date.now()
        }
      }));

      // Sync to backend
      await selectionsAPI.createBulkSelections(backendSelections);
      
      // Mark as synced
      localStorage.setItem(this.SYNC_KEY, now.toString());
      console.log(`Synced ${backendSelections.length} selections to backend`);

    } catch (error) {
      console.error('Failed to sync selections to backend:', error);
    }
  }

  /**
   * Restore selections from backend to localStorage
   */
  async restoreFromBackend(): Promise<void> {
    if (!this.isOnline || !this.isUserAuthenticated()) {
      return;
    }

    try {
      const backendSelections = await selectionsAPI.getUserSelections(1000);
      
      // Convert backend format to localStorage format
      const localSelections: Record<string, SelectionForm[]> = {};
      
      backendSelections.forEach(selection => {
        const localSelection = {
          chatId: selection.chat_id,
          messageId: selection.message_id,
          role: selection.role,
          text: selection.selected_text
        };

        if (!localSelections[selection.chat_id]) {
          localSelections[selection.chat_id] = [];
        }
        localSelections[selection.chat_id].push(localSelection);
      });

      // Save to localStorage
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(localSelections));
      console.log(`Restored ${backendSelections.length} selections from backend`);

    } catch (error) {
      console.error('Failed to restore selections from backend:', error);
    }
  }

  /**
   * Manually sync all localStorage selections to backend (useful for testing)
   */
  async manualSyncToBackend(): Promise<void> {
    console.log('Manual sync to backend initiated...');
    await this.syncToBackend();
  }

  /**
   * Clear all selections (both localStorage and backend)
   */
  async clearAllSelections(): Promise<void> {
    // Clear localStorage
    localStorage.removeItem(this.STORAGE_KEY);
    localStorage.removeItem(this.SYNC_KEY);

    // Clear backend if online and authenticated
    if (this.isOnline && this.isUserAuthenticated()) {
      try {
        const selections = await selectionsAPI.getUserSelections(1000);
        // Delete each selection (this could be optimized with a bulk delete endpoint)
        for (const selection of selections) {
          await selectionsAPI.deleteSelection(selection.id);
        }
        console.log('Cleared all selections from backend');
      } catch (error) {
        console.warn('Failed to clear selections from backend:', error);
      }
    }
  }

  // Private helper methods

  private isUserAuthenticated(): boolean {
    const currentUser = get(user);
    return currentUser !== null && currentUser !== undefined;
  }

  private saveToLocalStorage(selection: SelectionForm): void {
    try {
      const existing = JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '{}');
      
      if (!existing[selection.chat_id]) {
        existing[selection.chat_id] = [];
      }

      // Convert to local format
      const localSelection = {
        chatId: selection.chat_id,
        messageId: selection.message_id,
        role: selection.role,
        text: selection.selected_text
      };

      existing[selection.chat_id].push(localSelection);
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(existing));
    } catch (error) {
      console.error('Failed to save to localStorage:', error);
    }
  }

  private getFromLocalStorage(chatId: string): SelectionForm[] {
    try {
      const existing = JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '{}');
      return existing[chatId] || [];
    } catch (error) {
      console.error('Failed to get from localStorage:', error);
      return [];
    }
  }

  private getAllFromLocalStorage(): SelectionForm[] {
    try {
      const existing = JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '{}');
      const allSelections: SelectionForm[] = [];
      
      Object.values(existing).forEach((chatSelections: any) => {
        allSelections.push(...chatSelections);
      });
      
      return allSelections;
    } catch (error) {
      console.error('Failed to get all from localStorage:', error);
      return [];
    }
  }
}

// Export singleton instance
export const selectionSyncService = new SelectionSyncService();
