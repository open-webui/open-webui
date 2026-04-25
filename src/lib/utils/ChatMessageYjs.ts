import * as Y from 'yjs';
import { Socket } from 'socket.io-client';
import type { SessionUser } from '$lib/stores';

export function serializeOutput(output: any[]): string {
	let content = '';

	// First pass: collect function_call_output items by call_id for lookup
	const toolOutputs: { [key: string]: any } = {};
	for (const item of output) {
		if (item.type === 'function_call_output') {
			toolOutputs[item.call_id] = item;
		}
	}

	// Second pass: render items in order
	for (let idx = 0; idx < output.length; idx++) {
		const item = output[idx];
		const itemType = item.type || '';

		if (itemType === 'message') {
			for (const contentPart of item.content || []) {
				if ('text' in contentPart) {
					const text = contentPart.text?.trim() || '';
					if (text) {
						content = `${content}${text}\n`;
					}
				}
			}
		} else if (itemType === 'function_call') {
			if (content && !content.endsWith('\n')) {
				content += '\n';
			}

			const callId = item.call_id || '';
			const name = item.name || '';
			const args = item.arguments || '';

			const resultItem = toolOutputs[callId];
			if (resultItem) {
				let resultText = '';
				for (const resultOutput of resultItem.output || []) {
					if ('text' in resultOutput) {
						const outputText = resultOutput.text || '';
						resultText += typeof outputText === 'string' ? outputText : String(outputText);
					}
				}
				const files = resultItem.files;
				const embeds = resultItem.embeds || '';

				content += `<details type="tool_calls" done="true" id="${callId}" name="${name}" arguments='${JSON.stringify(args).replace(/'/g, '&apos;')}' result='${JSON.stringify(resultText).replace(/'/g, '&apos;')}' files='${JSON.stringify(files || '').replace(/'/g, '&apos;')}' embeds='${JSON.stringify(embeds).replace(/'/g, '&apos;')}'>
<summary>Tool Executed</summary>
</details>\n`;
			} else {
				content += `<details type="tool_calls" done="false" id="${callId}" name="${name}" arguments='${JSON.stringify(args).replace(/'/g, '&apos;')}'>
     <summary>Executing...</summary>
     </details>\n`;
			}
		} else if (itemType === 'function_call_output') {
			// Already handled inline with function_call above
			continue;
		} else if (itemType === 'reasoning') {
			let reasoningContent = '';
			const sourceList = item.summary || item.content || [];
			for (const contentPart of sourceList) {
				if ('text' in contentPart) {
					reasoningContent += contentPart.text || '';
				}
			}

			reasoningContent = reasoningContent.trim();
			const duration = item.duration;
			const status = item.status || 'in_progress';
			const isLastItem = idx === output.length - 1;

			if (content && !content.endsWith('\n')) {
				content += '\n';
			}

			const display = reasoningContent
				.split('\n')
				.map((line) => (line.startsWith('>') ? line : `> ${line}`))
				.join('\n');

			if (status === 'completed' || duration !== null || !isLastItem) {
				content = `${content}<details type="reasoning" done="true" duration="${duration || 0}">
     <summary>Thought for ${duration || 0} seconds</summary>
     ${display}
     </details>\n`;
			} else {
				content = `${content}<details type="reasoning" done="false">
     <summary>Thinking…</summary>
     ${display}
     </details>\n`;
			}
		} else if (itemType === 'open_webui:code_interpreter') {
			if (content && !content.endsWith('\n')) {
				content += '\n';
			}

			const code = item.code?.trim() || '';
			const lang = item.lang || 'python';
			const status = item.status || 'in_progress';
			const duration = item.duration;
			const isLastItem = idx === output.length - 1;

			let display = '';
			if (code) {
				display = `\`\`\`${lang}\n${code}\n\`\`\``;
			}

			let outputAttr = '';
			const ciOutput = item.output;
			if (ciOutput) {
				const outputJson =
					typeof ciOutput === 'object'
						? JSON.stringify(ciOutput)
						: JSON.stringify({ result: String(ciOutput) });
				outputAttr = ` output="${outputJson.replace(/"/g, '&quot;')}"`;
			}

			if (status === 'completed' || duration !== null || !isLastItem) {
				content += `<details type="code_interpreter" done="true" duration="${duration || 0}"${outputAttr}>
     <summary>Analyzed</summary>
     ${display}
     </details>\n`;
			} else {
				content += `<details type="code_interpreter" done="false"${outputAttr}>
     <summary>Analyzing…</summary>
     ${display}
     </details>\n`;
			}
		}
	}

	return content.trim();
}

export class ChatMessageYjsHandler {
	private doc: Y.Doc;
	private socket: Socket;
	private messageId: string;
	private onContentUpdate?: (content: string) => void;

	constructor(messageId: string, socket: Socket, onContentUpdate?: (content: string) => void) {
		this.messageId = messageId;
		this.socket = socket;
		this.onContentUpdate = onContentUpdate;
		this.doc = new Y.Doc();

		this.setupEventListeners();
	}

	private setupEventListeners() {
		// Listen for Yjs updates from backend
		this.socket.on('chat:completion', (data) => {
			if (data.yjs_update && data.message_id === this.messageId) {
				try {
					const update = new Uint8Array(
						data.yjs_update.match(/.{1,2}/g)?.map((byte) => parseInt(byte, 16)) || []
					);
					Y.applyUpdate(this.doc, update);

					// Get content, render and notify
					const output = this.doc.getArray('output').toArray();
					if (this.onContentUpdate) {
						this.onContentUpdate(serializeOutput(output));
					}
				} catch (error) {
					console.error('Error applying Yjs update:', error);
				}
			}
		});
	}

	public requestFullState() {
		this.socket.emit('chat:message:full_state', {
			message_id: this.messageId
		});
	}

	destroy() {
		this.socket.off('chat:completion');
	}
 }