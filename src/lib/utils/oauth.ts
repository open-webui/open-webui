/**
 * Decision logic for the OAUTH_AUTO_REDIRECT feature
 */

/** The subset of the /api/config payload the auto-redirect decision reads. */
export type AutoRedirectConfig = {
	oauth?: {
		providers?: Record<string, string>;
		auto_redirect?: boolean;
	};
	features?: {
		auth?: boolean;
		auth_trusted_header?: boolean;
		enable_login_form?: boolean;
		enable_ldap?: boolean;
	};
	onboarding?: boolean;
};

/** Per-visit signals that should suppress the auto-redirect. */
export type AutoRedirectContext = {
	/** True when a user session already exists ($user !== undefined). */
	isAuthenticated: boolean;
	/** The ?form= query param — when present the user explicitly wants the form. */
	formParam: string | null;
	/** The ?error= query param — keep the page so the error toast stays visible. */
	errorParam: string | null;
	/** A `token` cookie is set (an OAuth callback is mid-flight). */
	hasTokenCookie: boolean;
	/** A token is in localStorage (already signed in locally). */
	hasLocalStorageToken: boolean;
};

/**
 * Returns the OAuth provider login path to redirect to from /auth, or null
 * when the page should render normally.
 *
 * Redirects only when SSO is unambiguously the single intended entry point:
 * OAUTH_AUTO_REDIRECT is on, exactly one OAuth provider is configured, the
 * local login form and LDAP are both disabled, auth is enabled, the visitor
 * is unauthenticated, and nothing signals the form should be shown instead
 * (?form=, ?error=, an in-flight/stored token, trusted-header auth, or
 * first-run onboarding).
 *
 * The result is a root-relative path; callers prepend WEBUI_BASE_URL.
 */
export const getOAuthAutoRedirectPath = (
	config: AutoRedirectConfig | null | undefined,
	context: AutoRedirectContext
): string | null => {
	const providers = Object.keys(config?.oauth?.providers ?? {});

	const shouldRedirect =
		Boolean(config?.oauth?.auto_redirect) &&
		config?.features?.auth !== false &&
		providers.length === 1 &&
		config?.features?.enable_login_form === false &&
		config?.features?.enable_ldap === false &&
		!context.isAuthenticated &&
		!context.formParam &&
		!context.errorParam &&
		!context.hasTokenCookie &&
		!context.hasLocalStorageToken &&
		!(config?.features?.auth_trusted_header ?? false) &&
		!(config?.onboarding ?? false);

	return shouldRedirect ? `/oauth/${providers[0]}/login` : null;
};
