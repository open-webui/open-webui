/**
 * Attention Check Bank Module
 * 
 * Loads and manages attention check questions from the attention check bank CSV file.
 * Provides functions to randomly sample one attention check question.
 * 
 * @module attentionCheckBank
 */

// Q&A Pair interface for attention checks
export interface AttentionCheckQAPair {
	question: string;
	response: string;
}

// Attention check bank entry interface
export interface AttentionCheckBankEntry {
	scenario_id: string;
	trait_theme: string;
	trait_phrase: string;
	sentiment: string;
	prompt: string;
	response: string;
	trait_index: number;
	prompt_index: number;
}

// Cache for loaded attention check bank data
let cachedAttentionCheckBank: AttentionCheckBankEntry[] | null = null;

/**
 * Loads the attention check bank from CSV file.
 * 
 * Parses the attention_check_bank.csv file and converts it to an array of AttentionCheckBankEntry objects.
 * Results are cached to avoid re-parsing on subsequent calls.
 * 
 * @returns {Promise<AttentionCheckBankEntry[]>} Array of attention check bank entries
 * @throws {Error} If the CSV file cannot be loaded or parsed
 */
export async function loadAttentionCheckBank(): Promise<AttentionCheckBankEntry[]> {
	// Return cached data if available
	if (cachedAttentionCheckBank !== null) {
		return cachedAttentionCheckBank;
	}

	try {
		// Load CSV file from static directory
		const response = await fetch('/stat_analysis/attention_check_bank.csv');
		if (!response.ok) {
			throw new Error(`Failed to load attention check bank: ${response.statusText}`);
		}

		const csvText = await response.text();
		const lines = csvText.split('\n').filter(line => line.trim().length > 0);
		
		if (lines.length < 2) {
			throw new Error('Attention check bank CSV file is empty or invalid');
		}

		// Parse header
		const headers = lines[0].split(',').map(h => h.trim());
		const attentionCheckBank: AttentionCheckBankEntry[] = [];

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
				const entry: AttentionCheckBankEntry = {
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
					attentionCheckBank.push(entry);
				}
			}
		}

		// Cache the loaded data
		cachedAttentionCheckBank = attentionCheckBank;
		console.log(`✅ Loaded ${attentionCheckBank.length} attention check questions from bank`);
		
		return attentionCheckBank;
	} catch (error) {
		console.error('Error loading attention check bank:', error);
		throw error;
	}
}

/**
 * Randomly samples one attention check question from the attention check bank.
 * 
 * @returns {Promise<AttentionCheckQAPair | null>} A randomly sampled Q&A pair, or null if none available
 * @throws {Error} If attention check bank cannot be loaded
 * 
 * @example
 * // Get one random attention check question
 * const attentionCheck = await getRandomAttentionCheck();
 */
export async function getRandomAttentionCheck(): Promise<AttentionCheckQAPair | null> {
	// Load attention check bank
	const attentionCheckBank = await loadAttentionCheckBank();

	if (attentionCheckBank.length === 0) {
		console.warn('⚠️ No attention check questions available');
		return null;
	}

	// Randomly select one
	const randomIndex = Math.floor(Math.random() * attentionCheckBank.length);
	const selected = attentionCheckBank[randomIndex];

	// Convert to QAPair format
	const qaPair: AttentionCheckQAPair = {
		question: selected.prompt,
		response: selected.response
	};

	console.log(`✅ Sampled 1 random attention check question from bank`);
	return qaPair;
}

/**
 * Clears the cached attention check bank data.
 * 
 * Useful for testing or when the attention check bank file has been updated.
 */
export function clearAttentionCheckBankCache(): void {
	cachedAttentionCheckBank = null;
}




