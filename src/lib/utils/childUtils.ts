/**
 * Child Profile Utilities
 * 
 * Helper functions for managing child profile data and UUIDs
 */

import { childProfileSync } from '$lib/services/childProfileSync';

/**
 * Get the current child ID for selections
 * @returns string | null - The child UUID or null if no child selected
 */
export function getCurrentChildId(): string | null {
  if (typeof window === 'undefined') return null;
  
  try {
    // Get the current child ID from user settings via childProfileSync
    return childProfileSync.getCurrentChildId();
  } catch (error) {
    console.warn('Failed to get current child ID:', error);
    return null;
  }
}

/**
 * Get the current child marker for backward compatibility
 * @deprecated Use getCurrentChildId() instead
 * @returns string | null - The child marker or null if no child selected
 */
export function getCurrentChildMarker(): string | null {
  // For backward compatibility, return the child ID
  return getCurrentChildId();
}

/**
 * Get the current child profile object
 * @returns object | null - The current child profile or null if no child selected
 */
export function getCurrentChild(): any | null {
  if (typeof window === 'undefined') return null;
  
  try {
    // Get the current child profile from childProfileSync
    return childProfileSync.getCurrentChild();
  } catch (error) {
    console.warn('Failed to get current child:', error);
    return null;
  }
}

