import JSZip from 'jszip';

/**
 * 从文件中提取聊天记录数据
 * 支持 JSON 和 ZIP 格式
 *
 * @param file - 用户上传的文件 (JSON 或 ZIP)
 * @returns Promise<any> - 解析后的聊天记录数据
 * @throws Error - 文件格式不支持、ZIP 解压失败、JSON 解析失败等错误
 */
export async function extractChatsFromFile(file: File): Promise<any> {
	const fileExtension = file.name.split('.').pop()?.toLowerCase();

	if (fileExtension === 'json') {
		// 直接读取 JSON 文件
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = (e) => {
				try {
					const content = e.target?.result as string;
					const chats = JSON.parse(content);
					resolve(chats);
				} catch (error) {
					reject(new Error('Invalid JSON format'));
				}
			};
			reader.onerror = () => reject(new Error('Failed to read file'));
			reader.readAsText(file);
		});
	} else if (fileExtension === 'zip') {
		// 解压 ZIP 并提取 conversations.json
		try {
			const zip = await JSZip.loadAsync(file);
			const conversationsFile = zip.file('conversations.json');

			if (!conversationsFile) {
				throw new Error('conversations.json not found in ZIP archive');
			}

			const content = await conversationsFile.async('text');
			const chats = JSON.parse(content);
			return chats;
		} catch (error) {
			// 细化错误信息
			if (error instanceof Error) {
				if (error.message.includes('not found')) {
					throw new Error('ZIP file must contain conversations.json in root directory');
				} else if (error.message.includes('Unexpected token')) {
					throw new Error('conversations.json contains invalid JSON format');
				} else if (error.message.includes('corrupted')) {
					throw new Error('ZIP file is corrupted or invalid');
				} else {
					throw new Error(`Failed to extract ZIP file: ${error.message}`);
				}
			}
			throw new Error('Failed to process ZIP file');
		}
	} else {
		throw new Error('Unsupported file format. Please upload .json or .zip file');
	}
}
