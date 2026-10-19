type SlashCommandModel = {
	id?: string;
	owned_by?: string;
	info?: {
		meta?: {
			capabilities?: object;
		};
	};
};

export type SlashCommandSubmission =
	| { type: 'message'; content: string }
	| { type: 'compact' }
	| { type: 'status' }
	| { type: 'fork' }
	| { type: 'model'; modelId: string };

const modelUsesNativeSlashCommands = (model: SlashCommandModel | undefined) => {
	const capabilities = model?.info?.meta?.capabilities as
		| { native_slash_commands?: unknown }
		| undefined;
	return (
		model?.owned_by?.toLowerCase() === 'hermes' || capabilities?.native_slash_commands === true
	);
};

export const shouldPassThroughSlashCommands = (
	models: SlashCommandModel[],
	selectedModelIds: string[]
) => {
	const selectedIds = selectedModelIds.filter(Boolean);
	if (selectedIds.length === 0) return false;

	return selectedIds.every((id) =>
		modelUsesNativeSlashCommands(models.find((model) => model.id === id))
	);
};

export const resolveSlashCommandSubmission = (
	content: string,
	passThroughSlashCommands: boolean
): SlashCommandSubmission => {
	if (passThroughSlashCommands) return { type: 'message', content };

	const command = String(content).trim();
	if (command === '/compact') return { type: 'compact' };
	if (command === '/status') return { type: 'status' };
	if (command === '/fork') return { type: 'fork' };

	const modelCommand = command.match(/^\/model(?:\s+([\s\S]+))?$/);
	if (modelCommand) return { type: 'model', modelId: modelCommand[1]?.trim() ?? '' };

	return { type: 'message', content };
};
