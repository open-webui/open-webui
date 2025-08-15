/**
 * MCP Authentication Challenge Handler
 * Handles authentication challenges from MCP tools during execution
 */

export interface MCPAuthElicitationData {
	type: 'elicitation';
	data: {
		elicitation_type: string;
		title: string;
		message: string;
		server_id: string;
		server_name: string;
		tool_name: string;
		challenge_type: string;
		requires_reauth: boolean;
		auth_url?: string;
		instructions?: string;
		error_message: string;
	};
}

export interface MCPAuthState {
	showMCPAuthChallenge: boolean;
	mcpAuthElicitationData: MCPAuthElicitationData | {};
}

	export class MCPAuthHandler {
		private eventCallback: ((result: any) => void) | null = null;
		
		/**
		 * Check if a tool result contains an MCP authentication challenge
		 */
		static isAuthChallenge(toolResult: any): boolean {
			if (!toolResult || typeof toolResult !== 'object') return false;

			// Preferred structured elicitation shape
			if (
				toolResult.type === 'elicitation' &&
				toolResult.data &&
				(toolResult.data.elicitation_type === 'oauth_authentication' ||
				 toolResult.data.elicitation_type === 'manual_authentication')
			) {
				return true;
			}

			// Accept alternative shapes coming from backend where fields are flat or differently named
			const d = toolResult.data || toolResult;
			if (!d || typeof d !== 'object') return false;

			// Indicators of an auth challenge
			const hasReauthFlag = 'requires_reauth' in d && Boolean(d.requires_reauth);
			const hasChallengeType = typeof d.challenge_type === 'string' && d.challenge_type.length > 0;
			const hasAuthUrl = typeof d.auth_url === 'string' && d.auth_url.length > 0;
			const isAuthErrorType = d.error_type === 'authentication' || d.error_type === 'authentication_error';
			const isElicitationType = typeof d.elicitation_type === 'string' &&
				(d.elicitation_type === 'oauth_authentication' || d.elicitation_type === 'manual_authentication');
			const isHttp401 = d.status === 401 || d.http_status === 401;

			return Boolean(
				hasReauthFlag || hasChallengeType || hasAuthUrl || isAuthErrorType || isElicitationType || isHttp401
			);
		}

	/**
	 * Handle an authentication challenge by setting up the modal state
	 */
	handleAuthChallenge(
		toolResult: any,
		callback: (result: any) => void,
		state: MCPAuthState
	): boolean {
		if (!MCPAuthHandler.isAuthChallenge(toolResult)) {
			return false;
		}

		this.eventCallback = callback;
		state.showMCPAuthChallenge = true;
		// Normalize to { type:'elicitation', data:{...} }
		state.mcpAuthElicitationData = toolResult.type === 'elicitation' && toolResult.data
			? toolResult
			: { type: 'elicitation', data: toolResult.data || toolResult };
		
		return true;
	}

	/**
	 * Handle successful authentication (simple notify)
	 */
	handleAuthSuccess(state: MCPAuthState): void {
		if (this.eventCallback) {
			this.eventCallback(true);
		}
		
		this.cleanup(state);
	}

	/**
	 * Handle successful authentication with retry data
	 * Expects retryContext fields to instruct the backend to retry the tool call
	 */
	handleAuthSuccessWithRetry(state: MCPAuthState, retryContext: any): void {
		if (this.eventCallback && retryContext) {
			this.eventCallback({
				type: 'retry_tool',
				data: {
					server_id: retryContext.server_id,
					tool_name: retryContext.tool_name,
					arguments: retryContext.arguments,
					openai_tool_name: retryContext.openai_tool_name
				}
			});
		}
		this.cleanup(state);
	}

	/**
	 * Handle cancelled authentication
	 */
	handleAuthCancel(state: MCPAuthState): void {
		if (this.eventCallback) {
			this.eventCallback(false);
		}
		
		this.cleanup(state);
	}

	/**
	 * Clean up state after auth completion
	 */
	private cleanup(state: MCPAuthState): void {
		state.showMCPAuthChallenge = false;
		state.mcpAuthElicitationData = {};
		this.eventCallback = null;
	}
}