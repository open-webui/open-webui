const CONTENT_SECURITY_POLICY_META_TAG_PATTERN =
	/<meta\b[^>]*http-equiv\s*=\s*(['"])content-security-policy\1[^>]*>\s*/gi;

const escapeHtmlAttribute = (value: string) =>
	value
		.replace(/&/g, '&amp;')
		.replace(/"/g, '&quot;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;');

export const applyArtifactContentSecurityPolicy = (html: string, policy?: string | null) => {
	const normalizedPolicy = policy?.trim();

	if (!normalizedPolicy) {
		return html;
	}

	const contentSecurityPolicyMetaTag = `<meta http-equiv="Content-Security-Policy" content="${escapeHtmlAttribute(normalizedPolicy)}">`;
	const htmlWithoutExistingContentSecurityPolicy = html.replace(
		CONTENT_SECURITY_POLICY_META_TAG_PATTERN,
		''
	);

	if (/<head(\s[^>]*)?>/i.test(htmlWithoutExistingContentSecurityPolicy)) {
		return htmlWithoutExistingContentSecurityPolicy.replace(
			/<head(\s[^>]*)?>/i,
			(match) => `${match}${contentSecurityPolicyMetaTag}`
		);
	}

	if (/<html(\s[^>]*)?>/i.test(htmlWithoutExistingContentSecurityPolicy)) {
		return htmlWithoutExistingContentSecurityPolicy.replace(
			/<html(\s[^>]*)?>/i,
			(match) => `${match}<head>${contentSecurityPolicyMetaTag}</head>`
		);
	}

	const doctypeMatch = htmlWithoutExistingContentSecurityPolicy.match(/^\s*<!doctype[^>]*>\s*/i);

	if (doctypeMatch) {
		return `${doctypeMatch[0]}${contentSecurityPolicyMetaTag}${htmlWithoutExistingContentSecurityPolicy.slice(doctypeMatch[0].length)}`;
	}

	return `${contentSecurityPolicyMetaTag}${htmlWithoutExistingContentSecurityPolicy}`;
};
