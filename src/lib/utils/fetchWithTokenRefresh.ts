import { toast } from 'svelte-sonner';
import { user } from '$lib/stores';
import { userSignOut } from '$lib/apis/auths';

// Track redirecting state to prevent multiple redirects
let isRedirecting = false;

/**
 * Set up the global fetch interceptor to catch 401 Unauthorized responses
 * and redirect to login page when token expires
 */
export function setupFetchInterceptor() {
  // Store the original fetch function
  const originalFetch = window.fetch;
  
  // Replace the global fetch with our interceptor
  window.fetch = async function(input, init) {
    try {
      // Call the original fetch function
      const response = await originalFetch.apply(this, [input, init]);

      // Check for 302 redirects from proxy
      if (response.status === 302) {
        console.log('302 REDIRECT DETECTED - LIKELY PROXY SESSION EXPIRED', { 
          url: typeof input === 'string' ? input : input instanceof URL ? input.toString() : 'unknown',
          location: response.headers.get('location')
        });
        
        // Force logout and redirect immediately
        forceLogoutAndRedirect('Your proxy session has expired');
        return response; // Return the response even though we're redirecting
      }
      
      // Immediately check for 401 status without attempting to parse
      if (response.status === 401) {
        console.log('401 UNAUTHORIZED DETECTED - FORCING LOGOUT', { 
          url: typeof input === 'string' ? input : input instanceof URL ? input.toString() : 'unknown'
        });
        
        // Force logout and redirect immediately
        forceLogoutAndRedirect();
      }
      
      // Return the original response to preserve normal fetch behavior
      return response;
    } catch (error) {
      // Check if this error is authentication related
      const err = error as any; // Type assertion for better type checking
      if (err?.status === 401 || (typeof err?.message === 'string' && err.message.includes('unauthorized'))) {
        console.log('FETCH ERROR DETECTED - POSSIBLY AUTH RELATED', error);
        forceLogoutAndRedirect();
      }
      // Rethrow the error to preserve original behavior
      throw error;
    }
  };
  
  // Also set up a global AJAX error handler for APIs that might not use fetch
  window.addEventListener('unhandledrejection', function(event) {
    console.log('Unhandled promise rejection', event?.reason);
    const reason = event?.reason as any; // Type assertion
    if (reason?.status === 401) {
      console.log('401 ERROR IN UNHANDLED REJECTION - FORCING LOGOUT');
      forceLogoutAndRedirect();
    }
  });
  
  // Add storage event listener to coordinate across tabs
  window.addEventListener('storage', function(event) {
    if (event.key === 'token' && event.newValue === null) {
      // Token was removed in another tab
      console.log('TOKEN REMOVED IN ANOTHER TAB - REDIRECTING');
      window.location.reload();
    }
  });
  
  console.log('Token expiration interceptor installed successfully');
}

/**
 * Forces a logout and redirects the user to the login page.
 * This is used when a token is detected as expired.
 * Also calls userSignOut to properly expire the JWT token on the backend
 * and get the correct redirect URL.
 * 
 * @param customMessage Optional custom message to display during logout
 */
export async function forceLogoutAndRedirect(customMessage?: string) {
  // Prevent multiple redirects
  if (isRedirecting) return;
  isRedirecting = true;
  
  console.log('🔐 SESSION EXPIRED! FORCING LOGOUT AND PAGE RELOAD 🔐');
  
  try {
    // Clear user data locally
    user.set(undefined);

    // Remove token from localStorage
    localStorage.removeItem('token');
    
    // Try to call userSignOut to properly expire the server-side session
    // and get the redirect URL from the backend
    let redirectUrl: string | undefined;
    try {
      const res = await userSignOut();
      // Handle the custom response type which includes redirect_url
      const customRes = res as unknown as { redirect_url?: string };
      if (customRes?.redirect_url) {
        redirectUrl = customRes.redirect_url;
      }
    } catch (error) {
      console.error('Error signing out from server:', error);
      // Continue with client-side logout even if server logout fails
    }

    // Show notification
    toast.error(customMessage || 'Your session has expired. Logging you out...', {
      duration: 3000
    });
    
    // Use redirect URL from server if available, otherwise default to auth page
    if (redirectUrl) {
      window.location.href = redirectUrl;
    } else {
      // Force navigation to login page with hard reload
      const currentUrl = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/auth?redirect=${currentUrl}&expired=true&t=${Date.now()}`;
    }
    
    // As a backup, force reload after a short delay if redirect doesn't happen
    setTimeout(() => {
      window.location.reload();
    }, 1000);
    
  } catch (e) {
    console.error('Error during forced logout:', e);
    // Last resort: force reload
    window.location.reload();
  } finally {
    // Reset redirecting flag after a delay
    setTimeout(() => {
      isRedirecting = false;
    }, 5000);
  }
}
