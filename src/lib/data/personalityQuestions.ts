// Personality Q&A data loaded from JSON files
// This module loads the question-response pairs from the ContextBased_Prompt_Generation folder

export interface QAPair {
	question: string;
	response: string;
}

// Function to load JSON data dynamically
async function loadJSONFile(filename: string): Promise<Record<string, Record<string, string>>> {
	try {
		const response = await fetch(`/ContextBased_Prompt_Generation/${filename}`);
		if (!response.ok) {
			console.error(`Failed to load ${filename}:`, response.statusText);
			return {};
		}
		return await response.json();
	} catch (error) {
		console.error(`Error loading ${filename}:`, error);
		return {};
	}
}

// Cache for loaded JSON data
let cachedData: {
	agreeableness?: Record<string, Record<string, string>>;
	conscientiousness?: Record<string, Record<string, string>>;
	extraversion?: Record<string, Record<string, string>>;
	neuroticism?: Record<string, Record<string, string>>;
	openness?: Record<string, Record<string, string>>;
} = {};

// Load all personality trait data
export async function loadAllPersonalityData() {
	if (Object.keys(cachedData).length === 0) {
		const [agreeableness, conscientiousness, extraversion, neuroticism, openness] = await Promise.all([
			loadJSONFile('agreeableness.json'),
			loadJSONFile('conscientiousness.json'),
			loadJSONFile('extraversion.json'),
			loadJSONFile('neuroticism.json'),
			loadJSONFile('openness.json')
		]);
		
		cachedData = {
			agreeableness,
			conscientiousness,
			extraversion,
			neuroticism,
			openness
		};
	}
	
	return cachedData;
}

// Normalize apostrophes and quotes to handle encoding mismatches
// Converts curly quotes (U+2019, U+2018, U+201C, U+201D) to straight quotes (U+0027, U+0022)
function normalizeQuotes(str: string): string {
	return str
		.replace(/'/g, "'")  // Right single quotation mark (U+2019) → straight apostrophe
		.replace(/'/g, "'")  // Left single quotation mark (U+2018) → straight apostrophe
		.replace(/"/g, '"')  // Left double quotation mark (U+201C) → straight quote
		.replace(/"/g, '"');  // Right double quotation mark (U+201D) → straight quote
}

// Function to generate scenarios (Q&A pairs) from personality questions data
export async function generateScenariosFromPersonalityData(
	selectedCharacteristics: string[]
): Promise<QAPair[]> {
	const allScenarios: QAPair[] = [];
	
	if (!selectedCharacteristics || selectedCharacteristics.length === 0) {
		console.warn('No characteristics selected for scenario generation');
		return [];
	}
	
	// Load all personality data
	const personalityData = await loadAllPersonalityData();
	
	// For each selected characteristic, find Q&A pairs across all traits
	for (const charName of selectedCharacteristics) {
		const normalizedCharName = normalizeQuotes(charName);
		let found = false;
		let searchedTraits: string[] = [];
		
		// Search through all personality traits for the characteristic
		const allTraits = [
			{ name: 'agreeableness', data: personalityData.agreeableness },
			{ name: 'conscientiousness', data: personalityData.conscientiousness },
			{ name: 'extraversion', data: personalityData.extraversion },
			{ name: 'neuroticism', data: personalityData.neuroticism },
			{ name: 'openness', data: personalityData.openness }
		];
		
		for (const trait of allTraits) {
			searchedTraits.push(trait.name);
			
			if (trait.data) {
				// Try exact match first
				if (trait.data[charName]) {
					const qaPairs = Object.entries(trait.data[charName]).map(([question, response]) => ({
						question,
						response
					}));
					
					allScenarios.push(...qaPairs);
					found = true;
					console.log(`✓ Found characteristic "${charName}" in ${trait.name} (exact match): ${qaPairs.length} scenarios`);
					break;
				}
				
				// Try normalized match (handles apostrophe encoding mismatches)
				for (const jsonKey of Object.keys(trait.data)) {
					const normalizedJsonKey = normalizeQuotes(jsonKey);
					if (normalizedJsonKey === normalizedCharName) {
						const qaPairs = Object.entries(trait.data[jsonKey]).map(([question, response]) => ({
							question,
							response
						}));
						
						allScenarios.push(...qaPairs);
						found = true;
						console.log(`✓ Found characteristic "${charName}" in ${trait.name} (normalized match, JSON key: "${jsonKey}"): ${qaPairs.length} scenarios`);
						break;
					}
				}
				
				if (found) break;
			}
		}
		
		if (!found) {
			console.warn(`✗ Characteristic "${charName}" not found in any trait. Searched: ${searchedTraits.join(', ')}`);
		}
	}
	
	console.log(`Generated ${allScenarios.length} total scenarios from ${selectedCharacteristics.length} characteristics`);
	
	// Shuffle the scenarios
	const shuffled = allScenarios.sort(() => Math.random() - 0.5);
	
	// Return 10 random scenarios (or all if less than 10)
	return shuffled.slice(0, 10);
}

// Legacy function for compatibility - returns only questions
export async function getQuestionsFromCharacteristics(selectedCharacteristics: string[]): Promise<string[]> {
	const scenarios = await generateScenariosFromPersonalityData(selectedCharacteristics);
	return scenarios.map(s => s.question);
}

// Export for use in other files
export const personalityQuestions = {
	loadData: loadAllPersonalityData,
	generateScenarios: generateScenariosFromPersonalityData
};
