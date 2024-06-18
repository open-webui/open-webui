import CRC32 from 'crc-32';

export const parseFile = async (file) => {
	if (file.type === 'application/json') {
		return await parseJsonFile(file);
	} else if (file.type === 'image/png') {
		return await parsePngFile(file);
	} else {
		throw new Error('Unsupported file type');
	}
};

const parseJsonFile = async (file) => {
	const text = await file.text();
	const json = JSON.parse(text);

	const character = extractCharacter(json);

	return {
		file,
		json,
		formats: detectFormats(json),
		character
	};
};

const parsePngFile = async (file) => {
	const arrayBuffer = await file.arrayBuffer();
	const text = parsePngText(arrayBuffer);
	const json = JSON.parse(text);

	const image = URL.createObjectURL(file);
	const character = extractCharacter(json);

	return {
		file,
		json,
		image,
		formats: detectFormats(json),
		character
	};
};

const parsePngText = (arrayBuffer) => {
	const textChunkKeyword = 'chara';
	const chunks = readPngChunks(new Uint8Array(arrayBuffer));

	const textChunk = chunks
		.filter((chunk) => chunk.type === 'tEXt')
		.map((chunk) => decodeTextChunk(chunk.data))
		.find((entry) => entry.keyword === textChunkKeyword);

	if (!textChunk) {
		throw new Error(`No PNG text chunk named "${textChunkKeyword}" found`);
	}

	try {
		return new TextDecoder().decode(Uint8Array.from(atob(textChunk.text), (c) => c.charCodeAt(0)));
	} catch (e) {
		throw new Error('Unable to parse "chara" field as base64', e);
	}
};

const readPngChunks = (data) => {
	const isValidPng =
		data[0] === 0x89 &&
		data[1] === 0x50 &&
		data[2] === 0x4e &&
		data[3] === 0x47 &&
		data[4] === 0x0d &&
		data[5] === 0x0a &&
		data[6] === 0x1a &&
		data[7] === 0x0a;

	if (!isValidPng) throw new Error('Invalid PNG file');

	let chunks = [];
	let offset = 8; // Skip PNG signature

	while (offset < data.length) {
		let length =
			(data[offset] << 24) | (data[offset + 1] << 16) | (data[offset + 2] << 8) | data[offset + 3];
		let type = String.fromCharCode.apply(null, data.slice(offset + 4, offset + 8));
		let chunkData = data.slice(offset + 8, offset + 8 + length);
		let crc =
			(data[offset + 8 + length] << 24) |
			(data[offset + 8 + length + 1] << 16) |
			(data[offset + 8 + length + 2] << 8) |
			data[offset + 8 + length + 3];

		if (CRC32.buf(chunkData, CRC32.str(type)) !== crc) {
			throw new Error(`Invalid CRC for chunk type "${type}"`);
		}

		chunks.push({ type, data: chunkData, crc });
		offset += 12 + length;
	}

	return chunks;
};

const decodeTextChunk = (data) => {
	let i = 0;
	const keyword = [];
	const text = [];

	for (; i < data.length && data[i] !== 0; i++) {
		keyword.push(String.fromCharCode(data[i]));
	}

	for (i++; i < data.length; i++) {
		text.push(String.fromCharCode(data[i]));
	}

	return { keyword: keyword.join(''), text: text.join('') };
};

const extractCharacter = (json) => {
	function getTrimmedValue(json, keys) {
		return keys
			.map((key) => {
				const keyParts = key.split('.');
				let value = json;
				for (const part of keyParts) {
					if (value && value[part] != null) {
						value = value[part];
					} else {
						value = null;
						break;
					}
				}
				return value && value.trim();
			})
			.find((value) => value);
	}

	const name = getTrimmedValue(json, ['char_name', 'name', 'data.name']);
	const summary = getTrimmedValue(json, ['personality', 'title', 'data.description']);
	const personality = getTrimmedValue(json, ['char_persona', 'description', 'data.personality']);
	const scenario = getTrimmedValue(json, ['world_scenario', 'scenario', 'data.scenario']);
	const greeting = getTrimmedValue(json, [
		'char_greeting',
		'greeting',
		'first_mes',
		'data.first_mes'
	]);
	const examples = getTrimmedValue(json, [
		'example_dialogue',
		'mes_example',
		'definition',
		'data.mes_example'
	]);

	return { name, summary, personality, scenario, greeting, examples };
};

const detectFormats = (json) => {
	const formats = [];

	if (
		json.char_name &&
		json.char_persona &&
		json.world_scenario &&
		json.char_greeting &&
		json.example_dialogue
	)
		formats.push('Text Generation Character');
	if (
		json.name &&
		json.personality &&
		json.description &&
		json.scenario &&
		json.first_mes &&
		json.mes_example
	)
		formats.push('TavernAI Character');
	if (
		json.character &&
		json.character.name &&
		json.character.title &&
		json.character.description &&
		json.character.greeting &&
		json.character.definition
	)
		formats.push('CharacterAI Character');
	if (
		json.info &&
		json.info.character &&
		json.info.character.name &&
		json.info.character.title &&
		json.info.character.description &&
		json.info.character.greeting
	)
		formats.push('CharacterAI History');

	return formats;
};
