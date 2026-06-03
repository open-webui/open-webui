export const appendTaskIds = (taskIds: string[] | null, newTaskIds: string[]) => {
	return taskIds ? [...taskIds, ...newTaskIds] : newTaskIds;
};

export const canClearTaskIds = (
	completionTaskIdsGeneration: number,
	currentTaskIdsGeneration: number
) => currentTaskIdsGeneration === completionTaskIdsGeneration;
