// scripts/sync-translations.cjs
// Ensures all translation.json files have the same set of keys as the MASTER_LOCALE (en-US),
// preserving existing translations and removing keys not present in the master.
// Also ensures consistent sorting of all keys, including nested ones, with lowercase before uppercase.

const fs = require('fs');
const path = require('path');

const BASE_DIR = path.join(__dirname, '..', 'src', 'lib', 'i18n', 'locales');
const MASTER_LOCALE = 'en-US'; // The definitive source of truth for all keys
const MASTER_FILE_PATH = path.join(BASE_DIR, MASTER_LOCALE, 'translation.json');

/**
 * Recursively merges `source` into `target`.
 * Keys present in `source` but missing in `target` are added to `target`.
 * Keys present in both `source` and `target` are *preserved in `target`* if they are leaf nodes.
 * If both are objects, it recurses.
 * @param {object} target - The object to merge into.
 * @param {object} source - The object providing the structure and missing keys.
 * @param {object} masterSource - The master locale data (e.g., en-US) to use for default values for newly added leaf nodes.
 * @returns {boolean} True if any changes were made to the target object.
 */
function recursiveMergeAddMissing(target, source, masterSource) {
    let changed = false;

    for (const key in source) {
        if (Object.prototype.hasOwnProperty.call(source, key)) {
            const sourceValue = source[key];
            const targetValue = target[key];
            const masterValue = masterSource && Object.prototype.hasOwnProperty.call(masterSource, key) ? masterSource[key] : undefined;

            if (typeof sourceValue === 'object' && sourceValue !== null && !Array.isArray(sourceValue)) {
                // It's a nested object in the source
                if (typeof targetValue !== 'object' || targetValue === null || Array.isArray(targetValue)) {
                    // Target does not have a corresponding object, create one
                    target[key] = {};
                    changed = true;
                }
                // Recurse into the nested object
                // Pass the corresponding part of masterSource for default values
                if (recursiveMergeAddMissing(target[key], sourceValue, masterValue)) {
                    changed = true;
                }
            } else {
                // It's a leaf node (translation string)
                if (!Object.prototype.hasOwnProperty.call(target, key)) {
                    // Key is missing in the target locale, add it
                    target[key] = masterValue !== undefined ? masterValue : ""; // Use master value or empty string
                    changed = true;
                }
                // If the key already exists in target, its current value is preserved.
            }
        }
    }
    return changed;
}

/**
 * Recursively prunes keys from targetNode that are not present in canonicalNode.
 * @param {object} targetNode - The object to prune.
 * @param {object} canonicalNode - The object representing the allowed structure (derived from master).
 * @param {string} localeName - The name of the current locale for logging.
 * @param {string} [currentPath=''] - The current path for logging (e.g., "common.greeting").
 * @returns {boolean} True if any keys were deleted.
 */
function pruneOrphanedKeys(targetNode, canonicalNode, localeName, currentPath = '') {
    let nodeChanged = false;
    for (const key in targetNode) {
        if (Object.prototype.hasOwnProperty.call(targetNode, key)) {
            const fullKeyPath = currentPath ? `${currentPath}.${key}` : key;
            if (!Object.prototype.hasOwnProperty.call(canonicalNode, key)) {
                // Key exists in target but not in canonical, delete it
                delete targetNode[key];
                nodeChanged = true;
                console.warn(`[${localeName}] Removed orphaned key: '${fullKeyPath}'`);
            } else if (typeof targetNode[key] === 'object' && targetNode[key] !== null && !Array.isArray(targetNode[key])) {
                // If both are objects, recurse
                if (typeof canonicalNode[key] === 'object' && canonicalNode[key] !== null && !Array.isArray(canonicalNode[key])) {
                    if (pruneOrphanedKeys(targetNode[key], canonicalNode[key], localeName, fullKeyPath)) {
                        nodeChanged = true;
                    }
                } else {
                    // Type mismatch: target has object but canonical has a leaf value/different type
                    delete targetNode[key];
                    nodeChanged = true;
                    console.warn(`[${localeName}] Removed type-mismatched orphaned key: '${fullKeyPath}' (was object, should be leaf)`);
                }
            }
        }
    }
    return nodeChanged;
}

/**
 * Recursively sorts the keys of an object alphabetically using a custom localeCompare for desired case order.
 * @param {object} obj - The object whose keys need to be sorted.
 * @returns {object} A new object with keys sorted recursively.
 */
function sortObjectKeysAlphabetically(obj) {
    if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) {
        return obj; // Not an object, return as is
    }

    // Custom comparison function for sorting keys
    // 'en' is a common locale. You can make this configurable if needed.
    // sensitivity: 'case' ensures case differences are considered.
    // caseFirst: 'lower' ensures lowercase letters come before uppercase when other criteria are equal.
    const customKeySort = (keyA, keyB) => {
        return keyA.localeCompare(keyB, 'en', { sensitivity: 'case', caseFirst: 'lower' });
    };

    const sortedKeys = Object.keys(obj).sort(customKeySort);
    const newObj = {};

    sortedKeys.forEach(key => {
        newObj[key] = sortObjectKeysAlphabetically(obj[key]); // Recursively sort nested objects
    });

    return newObj;
}


function syncTranslations() {
    console.log('Starting translation synchronization...');

    const localeDirs = fs.readdirSync(BASE_DIR, { withFileTypes: true })
        .filter(dirent => dirent.isDirectory())
        .map(dirent => dirent.name);

    if (localeDirs.length === 0) {
        console.warn(`No locale directories found in ${BASE_DIR}. Aborting.`);
        return;
    }

    // Phase 1: Load the Master Locale (e.g., en-US) - This defines the canonical structure
    let masterLocaleData;
    try {
        if (!fs.existsSync(MASTER_FILE_PATH)) {
            console.error(`ERROR: Master locale file not found: ${MASTER_FILE_PATH}. This file is essential.`);
            process.exit(1);
        }
        const masterFileContent = fs.readFileSync(MASTER_FILE_PATH, 'utf8');
        masterLocaleData = JSON.parse(masterFileContent);
        console.log(`Loaded master locale: ${MASTER_LOCALE}/translation.json`);
    } catch (error) {
        console.error(`Error loading master locale ${MASTER_FILE_PATH}: ${error.message}`);
        process.exit(1); // Abort if master cannot be loaded
    }

    // The canonical structure is now strictly derived from the master locale
    // We'll sort the master data immediately so it dictates the order for others
    const canonicalStructure = sortObjectKeysAlphabetically(masterLocaleData);

    // Count keys in canonical structure for logging (optional, but good for feedback)
    const countKeys = (obj) => {
        let count = 0;
        for (const key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                    count += countKeys(obj[key]);
                } else {
                    count++;
                }
            }
        }
        return count;
    };
    const totalCanonicalKeys = countKeys(canonicalStructure);
    console.log(`Master locale has ${totalCanonicalKeys} keys. All other files will be synced to this structure and order.`);

    // Phase 2: Iterate through each locale and synchronize it with the canonical structure
    for (const dirName of localeDirs) {
        const filePath = path.join(BASE_DIR, dirName, 'translation.json');
        let currentFileData;

        // Load current locale's data, or start with an empty object if file is missing
        try {
            if (fs.existsSync(filePath)) {
                const fileContent = fs.readFileSync(filePath, 'utf8');
                currentFileData = JSON.parse(fileContent);
            } else {
                console.warn(`Translation file for ${dirName} is missing, creating an empty one.`);
                currentFileData = {};
            }
        } catch (error) {
            console.error(`Error loading or parsing ${filePath}: ${error.message}. Starting with an empty object for this locale.`);
            currentFileData = {};
        }

        console.log(`Processing ${dirName}/translation.json...`);

        let fileChangesMade = false;

        // First, add any missing keys from the canonical structure (master locale)
        const addedKeys = recursiveMergeAddMissing(currentFileData, canonicalStructure, masterLocaleData);
        if (addedKeys) {
            fileChangesMade = true;
        }

        // Then, prune orphaned keys (keys not present in the canonical structure)
        const prunedKeys = pruneOrphanedKeys(currentFileData, canonicalStructure, dirName);
        if (prunedKeys) {
            fileChangesMade = true;
        }

        // After all merges and prunes, re-sort the entire object to ensure consistent order
        // This is always applied regardless of `fileChangesMade` because existing files
        // might have incorrect sorting even if no keys were added/removed.
        const sortedData = sortObjectKeysAlphabetically(currentFileData);

        // To determine if a write is truly necessary, compare the stringified version
        // of the current data with the sorted data. This avoids unnecessary file writes
        // if only the in-memory representation was changed (e.g. by sorting an already sorted file).
        const currentContentFormatted = JSON.stringify(currentFileData, null, 2);
        const newContentFormatted = JSON.stringify(sortedData, null, 2);

        if (fileChangesMade || currentContentFormatted !== newContentFormatted) {
            fs.writeFileSync(filePath, newContentFormatted, 'utf8');
            console.log(`Updated ${dirName}/translation.json.`);
        } else {
            console.log(`${dirName}/translation.json is already in sync (keys and order).`);
        }
    }

    console.log('Translation synchronization complete.');
}

syncTranslations();