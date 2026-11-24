// Fixed labels for Open WebUI's own builtin tools, used when the model wrote none.
// Each t() call is a literal key so the i18n parser picks it up.

type Translate = (key: string) => string;
type Labels = [running: string, done: string, failed: string];

const labels = (t: Translate, name: string): Labels | null => {
	switch (name) {
		// Images and video
		case 'generate_image':
			return [t('Generating image'), t('Generated image'), t('Failed to generate image')];
		case 'edit_image':
			return [t('Editing image'), t('Edited image'), t('Failed to edit image')];
		case 'generate_video':
			return [t('Generating video'), t('Generated video'), t('Failed to generate video')];

		// Web and code
		case 'search_web':
			return [t('Searching the web'), t('Searched the web'), t('Failed to search the web')];
		case 'fetch_url':
			return [t('Reading web page'), t('Read web page'), t('Failed to read web page')];
		case 'execute_code':
			return [t('Running code'), t('Ran code'), t('Failed to run code')];

		// Time
		case 'get_current_timestamp':
			return [t('Checking the time'), t('Checked the time'), t('Failed to check the time')];
		case 'calculate_timestamp':
			return [t('Calculating date'), t('Calculated date'), t('Failed to calculate date')];
		case 'timer':
			return [t('Setting timer'), t('Set timer'), t('Failed to set timer')];

		// Memory
		case 'search_memories':
			return [t('Searching memories'), t('Searched memories'), t('Failed to search memories')];
		case 'list_memories':
			return [t('Listing memories'), t('Listed memories'), t('Failed to list memories')];
		case 'list_memory_paths':
			return [
				t('Listing memory paths'),
				t('Listed memory paths'),
				t('Failed to list memory paths')
			];
		case 'read_memory_path':
			return [t('Reading memories'), t('Read memories'), t('Failed to read memories')];
		case 'add_memory':
			return [t('Saving memory'), t('Saved memory'), t('Failed to save memory')];
		case 'update_memory':
			return [t('Updating memories'), t('Updated memories'), t('Failed to update memories')];
		case 'replace_memory_content':
			return [t('Updating memory'), t('Updated memory'), t('Failed to update memory')];
		case 'delete_memory':
			return [t('Deleting memory'), t('Deleted memory'), t('Failed to delete memory')];

		// Chats and users
		case 'search_chats':
			return [t('Searching chats'), t('Searched chats'), t('Failed to search chats')];
		case 'view_chat':
			return [t('Reading chat'), t('Read chat'), t('Failed to read chat')];
		case 'send_message':
			return [t('Sending message'), t('Sent message'), t('Failed to send message')];
		case 'search_users':
			return [t('Searching users'), t('Searched users'), t('Failed to search users')];

		// Notes
		case 'search_notes':
			return [t('Searching notes'), t('Searched notes'), t('Failed to search notes')];
		case 'view_note':
			return [t('Reading note'), t('Read note'), t('Failed to read note')];
		case 'write_note':
			return [t('Creating note'), t('Created note'), t('Failed to create note')];
		case 'replace_note_content':
			return [t('Updating note'), t('Updated note'), t('Failed to update note')];

		// Knowledge
		case 'list_knowledge':
			return [t('Listing knowledge'), t('Listed knowledge'), t('Failed to list knowledge')];
		case 'list_knowledge_bases':
			return [
				t('Listing knowledge bases'),
				t('Listed knowledge bases'),
				t('Failed to list knowledge bases')
			];
		case 'search_knowledge_bases':
			return [
				t('Searching knowledge bases'),
				t('Searched knowledge bases'),
				t('Failed to search knowledge bases')
			];
		case 'query_knowledge_bases':
		case 'query_knowledge_files':
		case 'grep_knowledge_files':
			return [t('Searching knowledge'), t('Searched knowledge'), t('Failed to search knowledge')];
		case 'search_knowledge_files':
			return [
				t('Searching knowledge files'),
				t('Searched knowledge files'),
				t('Failed to search knowledge files')
			];
		case 'view_knowledge_file':
			return [
				t('Reading knowledge file'),
				t('Read knowledge file'),
				t('Failed to read knowledge file')
			];
		case 'kb_exec':
			return [t('Browsing knowledge'), t('Browsed knowledge'), t('Failed to browse knowledge')];

		// Files
		case 'list_chat_files':
			return [t('Listing chat files'), t('Listed chat files'), t('Failed to list chat files')];
		case 'query_chat_files':
		case 'grep_chat_files':
			return [
				t('Searching chat files'),
				t('Searched chat files'),
				t('Failed to search chat files')
			];
		case 'view_file':
			return [t('Reading file'), t('Read file'), t('Failed to read file')];
		case 'display_file':
			return [t('Showing file'), t('Showed file'), t('Failed to show file')];

		// Channels
		case 'search_channels':
			return [t('Searching channels'), t('Searched channels'), t('Failed to search channels')];
		case 'search_channel_messages':
			return [
				t('Searching channel messages'),
				t('Searched channel messages'),
				t('Failed to search channel messages')
			];
		case 'view_channel_message':
			return [t('Reading message'), t('Read message'), t('Failed to read message')];
		case 'view_channel_thread':
			return [t('Reading thread'), t('Read thread'), t('Failed to read thread')];

		// Notifications
		case 'notify':
			return [t('Sending notification'), t('Sent notification'), t('Failed to send notification')];

		// Tasks
		case 'create_tasks':
			return [t('Creating tasks'), t('Created tasks'), t('Failed to create tasks')];
		case 'update_task':
			return [t('Updating task'), t('Updated task'), t('Failed to update task')];

		// Automations
		case 'create_automation':
			return [t('Creating automation'), t('Created automation'), t('Failed to create automation')];
		case 'update_automation':
			return [t('Updating automation'), t('Updated automation'), t('Failed to update automation')];
		case 'list_automations':
			return [t('Listing automations'), t('Listed automations'), t('Failed to list automations')];
		case 'toggle_automation':
			return [
				t('Pausing or resuming automation'),
				t('Paused or resumed automation'),
				t('Failed to pause or resume automation')
			];
		case 'delete_automation':
			return [t('Deleting automation'), t('Deleted automation'), t('Failed to delete automation')];

		// Calendar
		case 'search_calendar_events':
			return [t('Searching calendar'), t('Searched calendar'), t('Failed to search calendar')];
		case 'create_calendar_event':
			return [t('Creating event'), t('Created event'), t('Failed to create event')];
		case 'update_calendar_event':
			return [t('Updating event'), t('Updated event'), t('Failed to update event')];
		case 'delete_calendar_event':
			return [t('Deleting event'), t('Deleted event'), t('Failed to delete event')];

		// Skills and tools
		case 'view_skill':
		case 'read_skill_file':
			return [t('Reading skill'), t('Read skill'), t('Failed to read skill')];
		case 'grep_skill_files':
			return [t('Searching skill'), t('Searched skill'), t('Failed to search skill')];
		case 'update_skill_files':
			return [t('Updating skill'), t('Updated skill'), t('Failed to update skill')];
		case 'create_skill':
			return [t('Creating skill'), t('Created skill'), t('Failed to create skill')];
		case 'create_tool':
			return [t('Creating tool'), t('Created tool'), t('Failed to create tool')];
	}
	return null;
};

/**
 * The label for a tool call: a fixed failure label for builtins, else the model's label,
 * else the builtin's fixed label. Empty when there is none, so callers fall back to the name.
 */
export function toolCallLabel(
	attributes:
		| { name?: string; tool_id?: string; display_label?: string; running_label?: string }
		| undefined,
	done: boolean,
	failed: boolean,
	t: Translate
): string {
	const name = attributes?.name ?? '';
	const fixed = name && attributes?.tool_id === `builtin:${name}` ? labels(t, name) : null;
	return (
		(failed && fixed?.[2]) ||
		(done ? attributes?.display_label : attributes?.running_label) ||
		fixed?.[done ? 1 : 0] ||
		''
	);
}
