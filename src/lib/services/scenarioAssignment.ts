import { assignScenario, type ScenarioAssignResponse } from '$lib/apis/moderation';

/**
 * Assign scenarios for a child profile in the background.
 * All assignments are stored in the database via the API - no localStorage needed.
 *
 * @param childId - Child profile ID
 * @param participantId - User/participant ID
 * @param sessionNumber - Session number for this assignment
 * @param token - Authentication token
 * @param scenariosPerSession - Number of scenarios to assign (default: 6)
 * @returns Promise with success status, assignment count, and assignments
 */
export async function assignScenariosForChild(
	childId: string,
	participantId: string,
	sessionNumber: number,
	token: string,
	scenariosPerSession: number = 6
): Promise<{ success: boolean; assignmentCount: number; assignments: ScenarioAssignResponse[] }> {
	const assignments: ScenarioAssignResponse[] = [];
	let successCount = 0;

	try {
		for (let i = 0; i < scenariosPerSession; i++) {
			try {
				const response = await assignScenario(token, {
					participant_id: participantId,
					child_profile_id: childId,
					assignment_position: i,
					alpha: 1.0
				});
				assignments.push(response);
				successCount++;
				console.log(
					`✅ Assigned scenario ${i + 1}/${scenariosPerSession} for child ${childId}: ${response.scenario_id}`
				);
			} catch (error) {
				console.error(`❌ Error assigning scenario ${i + 1}/${scenariosPerSession}:`, error);
				// Continue with remaining assignments
			}
		}

		// Assignments are automatically stored in database via assignScenario API
		// No localStorage needed - will be retrieved from backend on scenario page load

		console.log(
			`✅ Completed scenario assignment for child ${childId}: ${successCount}/${scenariosPerSession} successful`
		);

		return {
			success: successCount === scenariosPerSession,
			assignmentCount: successCount,
			assignments
		};
	} catch (error) {
		console.error(`❌ Error in assignScenariosForChild for child ${childId}:`, error);
		return { success: false, assignmentCount: successCount, assignments };
	}
}
