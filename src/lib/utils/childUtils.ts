/**
 * Child Profile Utilities
 * 
 * Helper functions for managing child profile data and markers
 */

/**
 * Get the current child marker for selections
 * @returns string | null - The child marker (name or index) or null if no child selected
 */
export function getCurrentChildMarker(): string | null {
  if (typeof window === 'undefined') return null;
  
  try {
    // Get the selected child index
    const selectedIndex = localStorage.getItem('selectedChildIndex');
    if (selectedIndex === null) return null;
    
    const index = parseInt(selectedIndex);
    if (isNaN(index)) return null;
    
    // Get child profiles
    const profilesJson = localStorage.getItem('childProfiles');
    if (!profilesJson) return null;
    
    const profiles = JSON.parse(profilesJson);
    if (!Array.isArray(profiles) || profiles.length === 0) return null;
    
    // Get the current child
    const currentChild = profiles[index];
    if (!currentChild) return null;
    
    // Use child name as marker, fallback to index
    return currentChild.name || `child_${index}`;
  } catch (error) {
    console.warn('Failed to get current child marker:', error);
    return null;
  }
}

/**
 * Get the current child profile object
 * @returns object | null - The current child profile or null if no child selected
 */
export function getCurrentChild(): any | null {
  if (typeof window === 'undefined') return null;
  
  try {
    // Get the selected child index
    const selectedIndex = localStorage.getItem('selectedChildIndex');
    if (selectedIndex === null) return null;
    
    const index = parseInt(selectedIndex);
    if (isNaN(index)) return null;
    
    // Get child profiles
    const profilesJson = localStorage.getItem('childProfiles');
    if (!profilesJson) return null;
    
    const profiles = JSON.parse(profilesJson);
    if (!Array.isArray(profiles) || profiles.length === 0) return null;
    
    return profiles[index] || null;
  } catch (error) {
    console.warn('Failed to get current child:', error);
    return null;
  }
}

