import { toast } from 'svelte-sonner';
import { user } from '$lib/stores';
import { userSignOut } from '$lib/apis/auths';

// Track redirecting state to prevent multiple redirects
let isRedirecting = false;

// Allow custom handler to be set from layout.svelte
let sessionExpiryHandler: ((message?: string) => void) | null = null;

/**
 * Set the handler for session expiry
 * @param handler The function to call when a session expiry is detected
 */
export function setSessionExpiryHandler(handler: (message?: string) => void) {
  sessionExpiryHandler = handler;
  console.info('[Cursor] Session expiry handler set');
}

/**
 * Handle session expiry - either use the custom handler or fallback to forceLogoutAndRedirect
 */
function handleSessionExpiry(message?: string) {
  if (sessionExpiryHandler) {
    console.info('[Cursor] Using custom session expiry handler');
    sessionExpiryHandler(message);
  } else {
    console.info('[Cursor] No custom handler, using forceLogoutAndRedirect');
    forceLogoutAndRedirect(message);
  }
}

/**
 * Set up the global fetch interceptor to catch 401 Unauthorized responses
 * and redirect to login page when token expires
 */
export function setupFetchInterceptor() {
  // Store the original fetch function
  const originalFetch = window.fetch;
  
  // Get Microsoft Proxy domain if present
  const msProxyDomain = window.location.hostname.indexOf('msappproxy.net') >= 0 ? 
    window.location.hostname : null;
  
  // Replace the global fetch with our interceptor
  window.fetch = async function(input, init) {
    // Modify request to prevent automatic redirect following
    // This allows us to detect 302 redirects from Microsoft Entra
    const modifiedInit = {
      ...init,
      // Don't follow redirects automatically so we can detect them
      redirect: 'manual' as RequestRedirect
    };
    
    try {
      // Call the original fetch function with modified init
      const response = await originalFetch.apply(this, [input, modifiedInit]);
      
      // Get the request URL for logging
      const requestUrl = typeof input === 'string' ? input : input instanceof URL ? input.toString() : 'unknown';
      
      // Clone the response so we can check it without disturbing the original
      const responseClone = response.clone();
      
      console.info('setupFetchInterceptor responseClone', {
        status: responseClone.status,
        type: responseClone.type,
        url: responseClone.url,
        ok: responseClone.ok,
        requestUrl
      });
      
      // Check if the URL itself looks like an auth endpoint
      // This helps catch cases where the URL has already changed to an auth endpoint
      if (responseClone.url && (
          responseClone.url.indexOf('/oauth2/') >= 0 ||
          responseClone.url.indexOf('/auth/') >= 0 ||
          responseClone.url.indexOf('login.microsoftonline.com') >= 0 ||
          responseClone.url.indexOf('login.microsoft.com') >= 0
      )) {
        console.info('AUTH URL DETECTED IN RESPONSE - FORCING LOGOUT', {
          requestUrl,
          responseUrl: responseClone.url
        });
        handleSessionExpiry('Your session has expired');
      }
      
      // Check status without waiting for json parsing
      if (responseClone.status === 401) {
        console.info('401 UNAUTHORIZED DETECTED - FORCING LOGOUT', { 
          url: typeof input === 'string' ? input : input instanceof URL ? input.toString() : 'unknown'
        });
        
        // Force logout and redirect immediately
        handleSessionExpiry('Your session has expired');
      }
      
      // Check for 302 redirects from proxy - now we can catch these!
      // 'opaqueredirect' is the response type for cross-origin redirects when using manual redirect mode
      if (responseClone.status === 302 || responseClone.status === 307 || responseClone.type === 'opaqueredirect') {
        const location = responseClone.headers.get('location');
        
        console.info('REDIRECT DETECTED', { 
          requestUrl,
          responseType: responseClone.type,
          status: responseClone.status,
          location: location || 'No location header (opaque redirect)'
        });
        
        // For opaque redirects, we won't have a location header to check
        // So we need to make an educated guess based on circumstances
        if (responseClone.type === 'opaqueredirect') {
          // If we're on Microsoft Proxy, it's very likely this is an auth redirect
          if (msProxyDomain) {
            console.info('OPAQUE REDIRECT ON MICROSOFT PROXY - FORCING LOGOUT');
            handleSessionExpiry('Your proxy session has expired');
            // Still return response to allow normal error handling
          }
        }
        // For normal redirects, we can check the location
        else if (location && 
            (location.indexOf('login.microsoftonline.com') >= 0 || 
             location.indexOf('login.microsoft.com') >= 0)) {
          console.info('MICROSOFT ENTRA REDIRECT DETECTED - FORCING LOGOUT');
          handleSessionExpiry('Your proxy session has expired');
        }
      }
      
      // Return the original response to preserve normal fetch behavior
      // The API methods will still get their original response
      return response;
    } catch (error) {
      // Check if this is a CORS error from a redirect to Microsoft login
      const err = error as Error & { status?: number; redirectUrl?: string; detail?: string };
      
      // Log the error for debugging
      console.info('FETCH ERROR:', err);

      // Some endpoints return serialized errors with redirectUrl that point to auth endpoints
      if (err && typeof err === 'object') {
        // Check common auth-related fields in error responses
        if (
          (err.redirectUrl && (
            err.redirectUrl.indexOf('login.microsoft') >= 0 ||
            err.redirectUrl.indexOf('/oauth2/') >= 0
          )) ||
          (err.message && (
            err.message.indexOf('authentication') >= 0 ||
            err.message.indexOf('unauthorized') >= 0 ||
            err.message.indexOf('login') >= 0
          ))
        ) {
          console.info('AUTH-RELATED ERROR FIELDS DETECTED - FORCING LOGOUT', err);
          handleSessionExpiry('Your session has expired');
        }
      }
      
      // Check if this is an auth-related error
      if (err?.status === 401 || (typeof err?.message === 'string' && err.message.indexOf('unauthorized') >= 0)) {
        console.info('AUTH ERROR DETECTED - FORCING LOGOUT', err);
        handleSessionExpiry();
      }
      
      // Rethrow the error to preserve original behavior
      throw error;
    }
  };
  
  // Also set up a global AJAX error handler for APIs that might not use fetch
  window.addEventListener('unhandledrejection', function(event) {
    const reason = event?.reason as Error & { 
      status?: number; 
      detail?: string; 
      message?: string;
    };
    
    // Look for authentication errors in unhandled promise rejections
    if (reason?.status === 401 || 
        (reason?.detail && typeof reason.detail === 'string' && 
         (reason.detail.indexOf('not authenticated') >= 0 || reason.detail.indexOf('token') >= 0 || reason.detail.indexOf('auth') >= 0))) {
      console.info('AUTH ERROR IN UNHANDLED REJECTION - FORCING LOGOUT', reason);
      handleSessionExpiry();
      return;
    }
    
    // Check for CORS errors which might indicate Microsoft redirect
    if (reason instanceof TypeError && 
        reason.message && 
        (reason.message.indexOf('CORS') >= 0 || reason.message.indexOf('Failed to fetch') >= 0)) {
      console.info('CORS ERROR IN UNHANDLED REJECTION - POSSIBLY MS REDIRECT', reason);
      
      // If we're on Microsoft proxy domain, assume this is an auth error
      if (window.location.hostname.indexOf('msappproxy.net') >= 0) {
        handleSessionExpiry('Your proxy session has expired');
      }
    }
    
    // Also check for specific error messages in the reason object at any level
    const reasonStr = JSON.stringify(reason);
    if (reasonStr.indexOf('unauthorized') >= 0 || reasonStr.indexOf('authentication') >= 0 || reasonStr.indexOf('not logged in') >= 0) {
      console.info('AUTH-RELATED TEXT IN UNHANDLED REJECTION - FORCING LOGOUT', reason);
      handleSessionExpiry();
    }
  });
  
  console.info('Token expiration interceptor installed successfully');
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
  
  console.info('🔐 SESSION EXPIRED! FORCING LOGOUT AND PAGE RELOAD 🔐');
  
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
      // const currentUrl = encodeURIComponent(window.location.pathname + window.location.search);
      // window.location.href = `/auth?redirect=${currentUrl}&expired=true&t=${Date.now()}`;
      window.location.reload();
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
