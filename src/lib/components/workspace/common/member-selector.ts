export const shouldShowSelectableUser = (
	userId: string | null | undefined,
	currentUserId: string | null | undefined,
	includeCurrentUser = false
): boolean => {
	if (!userId) {
		return false;
	}

	return includeCurrentUser || userId !== currentUserId;
};
