export default function (options = {}) {
	return {
		extensions: [inlineIframeToken(options), blockIframeToken(options)]
	};
}

const inlineIframeToken = (options = {}) => {
	const WEBUI_BASE_URL = options.WEBUI_BASE_URL || '';
	const htmlIdToken = /{{HTML_FILE_ID_([a-f0-9-]+)}}/gi; // Regex to capture the HTML ID
	function tokenizer(src) {
		const match = htmlIdToken.exec(src);
		if (match) {
			return {
				type: 'iframe',
				raw: match[0],
				fileId: match[1]
			};
		}
	}
	function renderer(token) {
		const htmlUrl = `${WEBUI_BASE_URL}/api/v1/files/${token.fileId}/content`;
		const iframeElement = `<iframe src="${htmlUrl}" width="100%" frameborder="0" onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px';"></iframe>`;
		return iframeElement;
	}
	return {
		name: 'iframe',
		level: 'inline',
		tokenizer,
		renderer
	};
};

const blockIframeToken = (options = {}) => {
	const WEBUI_BASE_URL = options.WEBUI_BASE_URL || '';
	const htmlIdToken = /{{HTML_FILE_ID_([a-f0-9-]+)}}/gi; // Regex to capture the HTML ID
	function tokenizer(src) {
		const match = htmlIdToken.exec(src);
		if (match) {
			return {
				type: 'iframe',
				raw: match[0],
				fileId: match[1]
			};
		}
	}
	function renderer(token) {
		const htmlUrl = `${WEBUI_BASE_URL}/api/v1/files/${token.fileId}/content`;
		const iframeElement = `<iframe src="${htmlUrl}" width="100%" frameborder="0" onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px';"></iframe>`;
		return iframeElement;
	}
	return {
		name: 'iframe',
		level: 'block',
		tokenizer,
		renderer
	};
};
