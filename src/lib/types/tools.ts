// Basic representation of an OpenAPI Specification
export interface OpenAPISpec {
  openapi: string;
  info: {
    title: string;
    version: string;
    description?: string;
  };
  paths: Record<string, any>;
  components?: Record<string, any>;
  servers?: { url: string; description?: string }[];
}

// Represents a tool discovered from a local MCPO instance
export interface LocalMcpoToolConfig {
  id: string; // Unique identifier for the tool (e.g., derived from baseUrl + openapiPath)
  name: string; // Tool name, typically from openapi.info.title
  baseUrl: string; // Base URL of the MCPO instance (e.g., http://localhost:8000)
  openapiPath: string; // Path to the tool's OpenAPI spec on the MCPO instance (e.g., /time/openapi.json or /openapi.json if main spec)
  spec: OpenAPISpec; // The actual (potentially shared) OpenAPI specification document this tool operation comes from
  enabled?: boolean; // Whether the tool is enabled by the user

  // Fields to identify the specific operation if spec contains multiple
  pathKey: string;      // The path string, e.g., "/echo"
  methodKey: string;    // The HTTP method, e.g., "post"
  operationId?: string; // The operationId from the OpenAPI spec, if available
}

// General Tool type, can be extended or used as a base
export interface Tool {
  id: string;
  name: string;
  description?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  spec?: any; // Can be OpenAPISpec or other tool-specific spec
  type: 'openapi' | 'local_mcpo' | 'python_internal'; // Differentiates tool types
  enabled?: boolean;
  metadata?: Record<string, any>; // For any other relevant data
}

// Type for tool server connections (existing type, for context)
export interface ToolServerConnection {
  id: string;
  name: string;
  url: string;
  headers?: Record<string, string>;
  tools: Tool[]; // Tools provided by this server
  enabled?: boolean;
  last_error?: string | null;
  created_at?: string;
  updated_at?: string;
}
