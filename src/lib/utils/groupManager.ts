export const isGroupManagerAuthorizationFailure = (error: unknown) => {
	const status = (error as { status?: number } | null)?.status;
	return status === 401 || status === 403;
};

export const allGroupManagerRequestsDenied = (errors: unknown[]) =>
	errors.length > 0 && errors.every(isGroupManagerAuthorizationFailure);
