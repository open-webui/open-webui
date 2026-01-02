/**
 * Scenario Bank Module
 * 
 * Loads and manages scenarios from the scenario bank CSV file.
 * Provides functions to randomly sample scenarios independent of child characteristics.
 * 
 * @module scenarioBank
 */

// Q&A Pair interface for scenarios
export interface QAPair {
	question: string;
	response: string;
}

// Scenario bank entry interface
export interface ScenarioBankEntry {
	scenario_id: string;
	trait_theme: string;
	trait_phrase: string;
	sentiment: string;
	prompt: string;
	response: string;
	trait_index: number;
	prompt_index: number;
}

// Cache for loaded scenario bank data
let cachedScenarioBank: ScenarioBankEntry[] | null = null;

/**
 * Loads the scenario bank from CSV file.
 * 
 * Parses the scenario_bank.csv file and converts it to an array of ScenarioBankEntry objects.
 * Results are cached to avoid re-parsing on subsequent calls.
 * 
 * @returns {Promise<ScenarioBankEntry[]>} Array of scenario bank entries
 * @throws {Error} If the CSV file cannot be loaded or parsed
 */
export async function loadScenarioBank(): Promise<ScenarioBankEntry[]> {
	// Return cached data if available
	if (cachedScenarioBank !== null) {
		return cachedScenarioBank;
	}

	try {
		// Load CSV file from static directory
		const response = await fetch('/stat_analysis/scenario_bank.csv');
		if (!response.ok) {
			throw new Error(`Failed to load scenario bank: ${response.statusText}`);
		}

		const csvText = await response.text();
		const lines = csvText.split('\n').filter(line => line.trim().length > 0);
		
		if (lines.length < 2) {
			throw new Error('Scenario bank CSV file is empty or invalid');
		}

		// Parse header
		const headers = lines[0].split(',').map(h => h.trim());
		const scenarioBank: ScenarioBankEntry[] = [];

		// Parse data rows
		for (let i = 1; i < lines.length; i++) {
			const line = lines[i];
			// Handle CSV parsing with quoted fields
			const values: string[] = [];
			let currentValue = '';
			let inQuotes = false;

			for (let j = 0; j < line.length; j++) {
				const char = line[j];
				if (char === '"') {
					inQuotes = !inQuotes;
				} else if (char === ',' && !inQuotes) {
					values.push(currentValue.trim());
					currentValue = '';
				} else {
					currentValue += char;
				}
			}
			values.push(currentValue.trim()); // Add last value

			if (values.length >= headers.length) {
				const entry: ScenarioBankEntry = {
					scenario_id: values[0] || '',
					trait_theme: values[1] || '',
					trait_phrase: values[2] || '',
					sentiment: values[3] || '',
					prompt: values[4] || '',
					response: values[5] || '',
					trait_index: parseInt(values[6] || '0', 10) || 0,
					prompt_index: parseInt(values[7] || '0', 10) || 0
				};

				// Only add entries with valid prompt and response
				if (entry.prompt && entry.response) {
					scenarioBank.push(entry);
				}
			}
		}

		// Cache the loaded data
		cachedScenarioBank = scenarioBank;
		console.log(`✅ Loaded ${scenarioBank.length} scenarios from scenario bank`);
		
		return scenarioBank;
	} catch (error) {
		console.error('Error loading scenario bank:', error);
		throw error;
	}
}

/**
 * Randomly samples scenarios from the scenario bank.
 * 
 * Samples the specified number of scenarios without replacement, excluding
 * any scenarios that have already been seen (based on scenario_id).
 * 
 * @param {number} count - Number of scenarios to sample (default: 6)
 * @param {string[]} excludeIds - Array of scenario IDs to exclude from sampling
 * @returns {Promise<QAPair[]>} Array of randomly sampled Q&A pairs
 * @throws {Error} If scenario bank cannot be loaded or insufficient scenarios available
 * 
 * @example
 * // Sample 6 random scenarios, excluding already seen ones
 * const scenarios = await getRandomScenarios(6, ['A01P1', 'A02P2']);
 */
export async function getRandomScenarios(
	count: number = 6,
	excludeIds: string[] = []
): Promise<QAPair[]> {
	// Load scenario bank
	const scenarioBank = await loadScenarioBank();

	// Filter out excluded scenarios
	const availableScenarios = scenarioBank.filter(
		entry => !excludeIds.includes(entry.scenario_id)
	);

	if (availableScenarios.length < count) {
		console.warn(
			`⚠️ Only ${availableScenarios.length} scenarios available, requested ${count}. ` +
			`Returning all available scenarios.`
		);
		// Return all available if we don't have enough
		return availableScenarios.map(entry => ({
			question: entry.prompt,
			response: entry.response
		}));
	}

	// Fisher-Yates shuffle algorithm for random sampling
	const shuffled = [...availableScenarios];
	for (let i = shuffled.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1));
		[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
	}

	// Take first 'count' scenarios
	const selected = shuffled.slice(0, count);

	// Convert to QAPair format
	const qaPairs: QAPair[] = selected.map(entry => ({
		question: entry.prompt,
		response: entry.response
	}));

	console.log(`✅ Sampled ${qaPairs.length} random scenarios from bank`);
	return qaPairs;
}

/**
 * Clears the cached scenario bank data.
 * 
 * Useful for testing or when the scenario bank file has been updated.
 */
export function clearScenarioBankCache(): void {
	cachedScenarioBank = null;
}
