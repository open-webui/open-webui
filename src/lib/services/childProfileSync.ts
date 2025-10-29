/**
 * Child Profile Sync Service
 * 
 * Manages child profile data with localStorage caching and backend synchronization.
 * Provides offline support and cross-device sync via user settings.
 */

import { 
    getChildProfiles, 
    createChildProfile, 
    updateChildProfile, 
    deleteChildProfile,
    type ChildProfile,
    type ChildProfileForm 
} from '$lib/apis/child-profiles';
import { updateUserSettings } from '$lib/apis/users';
import { user } from '$lib/stores';
import { get } from 'svelte/store';

class ChildProfileSyncService {
    private readonly CACHE_KEY = 'child-profiles-cache';
    private readonly SYNC_KEY = 'child-profiles-synced';
    
    private isOnline = navigator.onLine;
    private isUserAuthenticated = () => !!get(user);

    constructor() {
        // Clean up any corrupted cache data on initialization
        this.validateAndCleanCache();
        
        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.syncFromBackend();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
    }
    
    /**
     * Validate and clean up corrupted cache data
     */
    private validateAndCleanCache(): void {
        try {
            const cached = localStorage.getItem(this.CACHE_KEY);
            if (cached) {
                const parsed = JSON.parse(cached);
                // If cache is not a valid array, clear it
                if (!Array.isArray(parsed)) {
                    console.warn('Clearing corrupted cache data');
                    this.clearCache();
                }
            }
        } catch (error) {
            console.warn('Error validating cache, clearing it:', error);
            this.clearCache();
        }
    }

    /**
     * Sync child profiles from backend to localStorage cache
     */
    async syncFromBackend(): Promise<ChildProfile[]> {
        if (!this.isOnline || !this.isUserAuthenticated()) {
            return this.getFromCache();
        }

        try {
            let token = get(user)?.token as string | undefined;
            if (!token && typeof localStorage !== 'undefined') {
                const lt = localStorage.getItem('token');
                if (lt && lt.length > 0) token = lt;
            }
            if (!token) return this.getFromCache();

            const profiles = await getChildProfiles(token);
            // Handle null response from API
            const safeProfiles = profiles || [];
            this.saveToCache(safeProfiles);
            localStorage.setItem(this.SYNC_KEY, 'true');
            return safeProfiles;
        } catch (error) {
            console.warn('Failed to sync child profiles from backend:', error);
            return this.getFromCache();
        }
    }

    /**
     * Get all child profiles (from cache or backend)
     */
    async getChildProfiles(): Promise<ChildProfile[]> {
        const cacheExists = localStorage.getItem(this.CACHE_KEY);
        const isSynced = localStorage.getItem(this.SYNC_KEY);
        
        // If no cache or not synced, try to sync from backend
        if (!cacheExists || !isSynced) {
            return await this.syncFromBackend();
        }
        
        // Return from cache
        return this.getFromCache();
    }

    /**
     * Create a new child profile
     */
    async createChildProfile(formData: ChildProfileForm): Promise<ChildProfile> {
        // Try to create on backend first if online and authenticated
        if (this.isOnline && this.isUserAuthenticated()) {
            try {
                let token = get(user)?.token as string | undefined;
                if (!token && typeof localStorage !== 'undefined') {
                    const lt = localStorage.getItem('token');
                    if (lt && lt.length > 0) token = lt;
                }
                if (token) {
                    const newProfile = await createChildProfile(token, formData);
                    // Update cache
                    let profiles = this.getFromCache();
                    // Extra safety check
                    if (!Array.isArray(profiles)) {
                        profiles = [];
                    }
                    profiles.push(newProfile);
                    this.saveToCache(profiles);
                    return newProfile;
                }
            } catch (error) {
                console.warn('Failed to create child profile on backend:', error);
            }
        }

        // Fallback: create locally (will be synced later)
        const localProfile: ChildProfile = {
            id: crypto.randomUUID(),
            user_id: get(user)?.id || 'local',
            name: formData.name,
            child_age: formData.child_age,
            child_gender: formData.child_gender,
            child_characteristics: formData.child_characteristics,
            parenting_style: formData.parenting_style,
            created_at: Date.now(),
            updated_at: Date.now()
        };

        let profiles = this.getFromCache();
        // Extra safety check
        if (!Array.isArray(profiles)) {
            profiles = [];
        }
        profiles.push(localProfile);
        this.saveToCache(profiles);
        
        return localProfile;
    }

    /**
     * Update an existing child profile
     */
    async updateChildProfile(profileId: string, formData: ChildProfileForm): Promise<ChildProfile> {
        // Try to update on backend first if online and authenticated
        if (this.isOnline && this.isUserAuthenticated()) {
            try {
                let token = get(user)?.token as string | undefined;
                if (!token && typeof localStorage !== 'undefined') {
                    const lt = localStorage.getItem('token');
                    if (lt && lt.length > 0) token = lt;
                }
                if (token) {
                    const updatedProfile = await updateChildProfile(token, profileId, formData);
                    // Update cache
                    let profiles = this.getFromCache();
                    // Extra safety check
                    if (!Array.isArray(profiles)) {
                        profiles = [];
                    }
                    const index = profiles.findIndex(p => p.id === profileId);
                    if (index !== -1) {
                        profiles[index] = updatedProfile;
                        this.saveToCache(profiles);
                    }
                    return updatedProfile;
                }
            } catch (error) {
                console.warn('Failed to update child profile on backend:', error);
            }
        }

        // Fallback: update locally
        let profiles = this.getFromCache();
        // Extra safety check
        if (!Array.isArray(profiles)) {
            profiles = [];
        }
        const index = profiles.findIndex(p => p.id === profileId);
        if (index !== -1) {
            profiles[index] = {
                ...profiles[index],
                ...formData,
                updated_at: Date.now()
            };
            this.saveToCache(profiles);
            return profiles[index];
        }

        throw new Error('Child profile not found');
    }

    /**
     * Delete a child profile
     */
    async deleteChildProfile(profileId: string): Promise<void> {
        // Try to delete on backend first if online and authenticated
        if (this.isOnline && this.isUserAuthenticated()) {
            try {
                let token = get(user)?.token as string | undefined;
                if (!token && typeof localStorage !== 'undefined') {
                    const lt = localStorage.getItem('token');
                    if (lt && lt.length > 0) token = lt;
                }
                if (token) {
                    await deleteChildProfile(token, profileId);
                    // Update cache
                    let profiles = this.getFromCache();
                    // Extra safety check
                    if (!Array.isArray(profiles)) {
                        profiles = [];
                    }
                    profiles = profiles.filter(p => p.id !== profileId);
                    this.saveToCache(profiles);
                    return;
                }
            } catch (error) {
                console.warn('Failed to delete child profile on backend:', error);
            }
        }

        // Fallback: delete locally
        let profiles = this.getFromCache();
        // Extra safety check
        if (!Array.isArray(profiles)) {
            profiles = [];
        }
        profiles = profiles.filter(p => p.id !== profileId);
        this.saveToCache(profiles);
    }

    /**
     * Get the currently selected child profile
     */
    getCurrentChild(): ChildProfile | null {
        const currentUserId = get(user)?.id;
        if (!currentUserId) return null;

        const selectedChildId = this.getCurrentChildId();
        if (!selectedChildId) return null;

        let profiles = this.getFromCache();
        // Extra safety check
        if (!Array.isArray(profiles)) {
            profiles = [];
        }
        return profiles.find(p => p.id === selectedChildId) || null;
    }

    /**
     * Get the currently selected child ID from user settings
     */
    getCurrentChildId(): string | null {
        const userData = get(user);
        if (!userData?.settings?.ui?.selectedChildId) return null;
        
        return userData.settings.ui.selectedChildId;
    }

    /**
     * Set the currently selected child ID in user settings
     */
    async setCurrentChildId(childId: string | null): Promise<void> {
        const userData = get(user);
        if (!userData?.token) return;

        try {
            const currentSettings = userData.settings || {};
            const currentUI = currentSettings.ui || {};
            
            if (childId) {
                currentUI.selectedChildId = childId;
            } else {
                delete currentUI.selectedChildId;
            }
            
            currentSettings.ui = currentUI;

            await updateUserSettings(userData.token, currentSettings);
            
            // Update local user store
            user.update(u => ({
                ...u,
                settings: currentSettings
            }));
        } catch (error) {
            console.error('Failed to update selected child in user settings:', error);
            throw error;
        }
    }

    /**
     * Get child profiles from localStorage cache
     */
    private getFromCache(): ChildProfile[] {
        try {
            const cached = localStorage.getItem(this.CACHE_KEY);
            if (!cached) return [];
            
            const parsed = JSON.parse(cached);
            // Ensure the parsed value is a valid array
            if (!parsed || !Array.isArray(parsed)) {
                console.warn('Cache contained invalid data, resetting to empty array');
                return [];
            }
            return parsed;
        } catch (error) {
            console.warn('Failed to parse child profiles cache:', error);
            return [];
        }
    }

    /**
     * Save child profiles to localStorage cache
     */
    private saveToCache(profiles: ChildProfile[]): void {
        try {
            localStorage.setItem(this.CACHE_KEY, JSON.stringify(profiles));
        } catch (error) {
            console.warn('Failed to save child profiles to cache:', error);
        }
    }

    /**
     * Clear all cached child profile data
     */
    clearCache(): void {
        localStorage.removeItem(this.CACHE_KEY);
        localStorage.removeItem(this.SYNC_KEY);
    }
}

// Export singleton instance
export const childProfileSync = new ChildProfileSyncService();
