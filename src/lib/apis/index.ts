import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
import { convertOpenApiToToolPayload } from '$lib/utils';
import { getOpenAIModelsDirect } from './openai';
import { handleApiUnauthorized } from '$lib/stores';

import { parse } from 'yaml';
import { toast } from 'svelte-sonner';

export const getModels = async (
    token: string = '',
    connections: object | null = null,
    base: boolean = false
) => {
    let error = null;
    const res = await fetch(`${WEBUI_BASE_URL}/api/models${base ? '/base' : ''}`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        }
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            error = err;
            console.log(err);
            return null;
        });

    if (error && res === null) { // Throw only if fetch itself failed or 401 occurred and was handled by returning null
        throw error;
    }

    // Proceed with model processing only if res is not null
    let models = res?.data ?? [];

    if (connections && !base && res) { // Check res is not null before proceeding
        let localModels = [];

        // Keep the existing logic for fetching direct OpenAI models
        // getOpenAIModelsDirect does not use the internal token, so no 401 check needed within its call here.
        // The outer getModels call already handled its own potential 401.
        if (connections) {
            const OPENAI_API_BASE_URLS = connections.OPENAI_API_BASE_URLS;
            const OPENAI_API_KEYS = connections.OPENAI_API_KEYS;
            const OPENAI_API_CONFIGS = connections.OPENAI_API_CONFIGS;

            const requests = [];
            for (const idx in OPENAI_API_BASE_URLS) {
                const url = OPENAI_API_BASE_URLS[idx];

                if (idx.toString() in OPENAI_API_CONFIGS) {
                    const apiConfig = OPENAI_API_CONFIGS[idx.toString()] ?? {};

                    const enable = apiConfig?.enable ?? true;
                    const modelIds = apiConfig?.model_ids ?? [];

                    if (enable) {
                        if (modelIds.length > 0) {
                            const modelList = {
                                object: 'list',
                                data: modelIds.map((modelId) => ({
                                    id: modelId,
                                    name: modelId,
                                    owned_by: 'openai',
                                    openai: { id: modelId },
                                    urlIdx: idx
                                }))
                            };

                            requests.push(
                                (async () => {
                                    return modelList;
                                })()
                            );
                        } else {
                            requests.push(
                                (async () => {
                                    // This uses getOpenAIModelsDirect which handles its own fetch without internal token
                                    return await getOpenAIModelsDirect(url, OPENAI_API_KEYS[idx])
                                        .then((res) => {
                                            return res;
                                        })
                                        .catch((err) => {
                                            console.error(`Error fetching direct models from ${url}:`, err); // Log specific error
                                            return {
                                                object: 'list',
                                                data: [],
                                                urlIdx: idx // Ensure urlIdx is attached even on error for proper mapping later
                                            };
                                        });
                                })()
                            );
                        }
                    } else {
                        requests.push(
                            (async () => {
                                return {
                                    object: 'list',
                                    data: [],
                                    urlIdx: idx
                                };
                            })()
                        );
                    }
                }
            }

            const responses = await Promise.all(requests);

            for (const idx in responses) {
                // Ensure proper indexing if requests array doesn't align perfectly with original idx keys
                const response = responses[idx];
                const responseUrlIdx = response?.urlIdx ?? idx; // Get urlIdx attached in the response/error object
                const apiConfig = OPENAI_API_CONFIGS[responseUrlIdx.toString()] ?? {};

                let responseModels = Array.isArray(response) ? response : (response?.data ?? []);
                responseModels = responseModels.map((model) => ({ ...model, openai: { id: model.id }, urlIdx: responseUrlIdx }));

                const prefixId = apiConfig.prefix_id;
                if (prefixId) {
                    for (const model of responseModels) {
                        model.id = `${prefixId}.${model.id}`;
                    }
                }

                const tags = apiConfig.tags;
                if (tags) {
                    for (const model of responseModels) {
                        model.tags = tags;
                    }
                }

                localModels = localModels.concat(responseModels);
            }
        }

        models = models.concat(
            localModels.map((model) => ({
                ...model,
                name: model?.name ?? model?.id,
                direct: true
            }))
        );

        // Remove duplicates
        const modelsMap = {};
        for (const model of models) {
            modelsMap[model.id] = model;
        }

        models = Object.values(modelsMap);
    } else if(error) {
        // If the initial fetch failed (error is set, res is null), return empty array
        return [];
    }


    return models.sort((a, b) => a.name.localeCompare(b.name)); // Sort at the end
};

type ChatCompletedForm = {
    model: string;
    messages: string[];
    chat_id: string;
    session_id: string;
};

export const chatCompleted = async (token: string, body: ChatCompletedForm) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/chat/completed`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        },
        body: JSON.stringify(body)
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

type ChatActionForm = {
    model: string;
    messages: string[];
    chat_id: string;
};

export const chatAction = async (token: string, action_id: string, body: ChatActionForm) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/chat/actions/${action_id}`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        },
        body: JSON.stringify(body)
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const stopTask = async (token: string, id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/tasks/stop/${id}`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        }
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getTaskIdsByChatId = async (token: string, chat_id: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/tasks/chat/${chat_id}`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        }
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res ?? []; // Assuming it returns a list of IDs
};

export const getToolServerData = async (token: string, url: string) => {
    let error = null;
    let parsedResponse = null;

    await fetch(`${url}`, { // The URL itself might contain `/openapi.json` etc.
        method: 'GET',
        headers: {
            Accept: 'application/json', // Accept JSON, but handle YAML specifically later
            // 'Content-Type': 'application/json', // Content-Type is for request body, not needed for GET
            ...(token && { authorization: `Bearer ${token}` }) // Use the passed token
        }
    })
        .then(async (res) => {
            // Check 401 *before* checking content type or reading body
            if (res.status === 401 && token) { handleApiUnauthorized(); throw new Error('Unauthorized'); }

            // Check if URL ends with .yaml or .yml to determine format
            if (url.toLowerCase().endsWith('.yaml') || url.toLowerCase().endsWith('.yml')) {
                if (!res.ok) throw new Error(`HTTP error: ${res.status} ${res.statusText} (YAML)`);
                const text = await res.text();
                parsedResponse = parse(text); // Parse YAML
            } else {
                // Assume JSON for other cases
                if (!res.ok) {
                    // Attempt to parse JSON error, fallback to text
                    let errorBody = await res.text();
                    try { errorBody = JSON.parse(errorBody); } catch(e) {/* ignore JSON parse error */}
                    throw errorBody; // Throw parsed error or text
                }
                parsedResponse = await res.json(); // Parse JSON
            }
        })
        .catch((err) => {
            console.log(err); // Log the raw error
            if (err instanceof Error) { // Handle Error objects thrown
                error = err.message;
            } else if (typeof err === 'object' && err !== null && 'detail' in err) {
                error = err.detail; // Handle FastAPI-like error details
            } else {
                error = String(err); // Fallback for other error types
            }
            // No return null here, error will be checked below
        });

    if (error) {
        throw error; // Throw the captured error message
    }

    if (parsedResponse === null) {
        throw new Error('Failed to fetch or parse tool server data'); // Should not happen if no error thrown, but safeguard
    }

    // Process the parsed response (either from JSON or YAML)
    const data = {
        openapi: parsedResponse,
        info: parsedResponse.info,
        specs: convertOpenApiToToolPayload(parsedResponse) // Assuming this util works for parsed YAML too
    };

    console.log(data);
    return data;
};


// This function uses getToolServerData internally, which now handles 401.
// The token passed to getToolServerData needs to be correct (internal token or server key).
export const getToolServersData = async (i18n, servers: object[]) => {
    return (
        await Promise.all(
            servers
                .filter((server) => server?.config?.enable)
                .map(async (server) => {
                    // Determine the correct token to use: server key if bearer, otherwise internal token
                    const serverToken = (server?.auth_type ?? 'bearer') === 'bearer' ? server?.key : localStorage.token;
                    const serverUrl = server?.url + '/' + (server?.path ?? 'openapi.json');

                    const data = await getToolServerData(serverToken, serverUrl)
                    .catch((err) => {
                        // Toast the error message (getToolServerData now throws the error message)
                        toast.error(
                            i18n.t(`Failed to connect to {{URL}} OpenAPI tool server: {{ERROR}}`, {
                                URL: serverUrl,
                                ERROR: err instanceof Error ? err.message : String(err)
                            })
                        );
                        return null;
                    });

                    if (data) {
                        const { openapi, info, specs } = data;
                        return {
                            url: server?.url, // Base URL without path
                            openapi: openapi,
                            info: info,
                            specs: specs
                        };
                    }
                    return null; // Ensure null is returned if data is null
                })
        )
    ).filter((server) => server); // Filter out null results from failed fetches
};

// This function uses the passed token for the actual tool execution request
export const executeToolServer = async (
    token: string, // This is the internal user token OR the specific tool server API key based on context
    url: string, // Base URL of the tool server
    name: string, // operationId
    params: Record<string, any>,
    serverData: { openapi: any; info: any; specs: any }
) => {
    let error = null;
    let result = null;

    try {
        // ... (keep the existing logic for finding route, method, params) ...
        const matchingRoute = Object.entries(serverData.openapi.paths).find(([_, methods]) =>
            Object.entries(methods as any).some(([__, operation]: any) => operation.operationId === name)
        );

        if (!matchingRoute) {
            throw new Error(`No matching route found for operationId: ${name}`);
        }
        // ... (rest of the existing logic for preparing URL and options) ...

        const [routePath, methods] = matchingRoute;
        const methodEntry = Object.entries(methods as any).find(
            ([_, operation]: any) => operation.operationId === name
        );

        if (!methodEntry) {
            throw new Error(`No matching method found for operationId: ${name}`);
        }
        const [httpMethod, operation]: [string, any] = methodEntry;

        const pathParams: Record<string, any> = {};
        const queryParams: Record<string, any> = {};
        let bodyParams: any = {};

        if (operation.parameters) {
            operation.parameters.forEach((param: any) => {
                const paramName = param.name;
                const paramIn = param.in;
                if (params.hasOwnProperty(paramName)) {
                    if (paramIn === 'path') {
                        pathParams[paramName] = params[paramName];
                    } else if (paramIn === 'query') {
                        queryParams[paramName] = params[paramName];
                    }
                }
            });
        }

        let finalUrl = `${url}${routePath}`;
        Object.entries(pathParams).forEach(([key, value]) => {
            finalUrl = finalUrl.replace(new RegExp(`{${key}}`, 'g'), encodeURIComponent(value));
        });
        if (Object.keys(queryParams).length > 0) {
            const queryString = new URLSearchParams(
                Object.entries(queryParams).map(([k, v]) => [k, String(v)])
            ).toString();
            finalUrl += `?${queryString}`;
        }

        if (operation.requestBody && operation.requestBody.content) {
            // Assume all remaining params not used in path/query are for the body
            const usedParams = new Set([...Object.keys(pathParams), ...Object.keys(queryParams)]);
            bodyParams = Object.entries(params)
                .filter(([key]) => !usedParams.has(key))
                .reduce((obj, [key, value]) => {
                    obj[key] = value;
                    return obj;
                }, {});
        }


        const headers: Record<string, string> = {
            // Assume JSON unless specified otherwise in OpenAPI spec (more complex handling needed for full compliance)
            'Content-Type': 'application/json',
            'Accept': 'application/json', // Prefer JSON response
            ...(token && { authorization: `Bearer ${token}` }) // Use the provided token/key
        };

        let requestOptions: RequestInit = {
            method: httpMethod.toUpperCase(),
            headers
        };

        if (['post', 'put', 'patch'].includes(httpMethod.toLowerCase()) && Object.keys(bodyParams).length > 0) {
            requestOptions.body = JSON.stringify(bodyParams);
        }

        const res = await fetch(finalUrl, requestOptions);

        // Check 401 after fetch
        if (res.status === 401 && token) {
            handleApiUnauthorized();
            throw new Error('Unauthorized executing tool server');
        }

        if (!res.ok) {
            const resText = await res.text();
            throw new Error(`HTTP error! Status: ${res.status}. Message: ${resText}`);
        }

        // Try to parse JSON, fall back to text if it fails
        try {
            result = await res.json();
        } catch (jsonError) {
            result = await res.text(); // Use text if JSON parsing fails
        }

    } catch (err: any) {
        error = err.message;
        console.error('API Request Error (executeToolServer):', error);
        result = { error }; // Return error structure consistent with original code
    }

    // No explicit throw here, original code returned { error } structure
    return result;
};

export const getTaskConfig = async (token: string = '') => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/config`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        }
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const updateTaskConfig = async (token: string, config: object) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/config/update`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        },
        body: JSON.stringify(config)
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const generateTitle = async (
    token: string = '',
    model: string,
    messages: string[],
    chat_id?: string
) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/title/completions`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            model: model,
            messages: messages,
            ...(chat_id && { chat_id: chat_id })
        })
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        // Original code returned 'New Chat' on error, let's keep that
        console.error("Error generating title:", error);
        // throw error; // Or uncomment to throw
    }

    // Return default title if res is null (due to error) or parsing fails
    return res?.choices[0]?.message?.content.replace(/["']/g, '') ?? 'New Chat';
};

export const generateTags = async (
    token: string = '',
    model: string,
    messages: string, // Assuming this should be object[] like title? Keeping as string per original code
    chat_id?: string
) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/tags/completions`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            model: model,
            messages: messages,
            ...(chat_id && { chat_id: chat_id })
        })
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        // Original code returned empty array on error
        console.error("Error generating tags:", error);
        // throw error; // Or uncomment to throw
        return [];
    }

    try {
        // Step 1: Safely extract the response string
        const response = res?.choices[0]?.message?.content ?? '';
        if (!response) return []; // Return empty if no content

        // Step 2: Attempt to fix common JSON format issues like single quotes
        const sanitizedResponse = response.replace(/['‘’`]/g, '"'); // Convert single quotes to double quotes for valid JSON

        // Step 3: Find the relevant JSON block within the response
        const jsonStartIndex = sanitizedResponse.indexOf('{');
        const jsonEndIndex = sanitizedResponse.lastIndexOf('}');

        // Step 4: Check if we found a valid JSON block (with both `{` and `}`)
        if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
            const jsonResponse = sanitizedResponse.substring(jsonStartIndex, jsonEndIndex + 1);

            // Step 5: Parse the JSON block
            const parsed = JSON.parse(jsonResponse);

            // Step 6: If there's a "tags" key, return the tags array; otherwise, return an empty array
            if (parsed && parsed.tags) {
                // Ensure it's an array of strings
                return Array.isArray(parsed.tags) ? parsed.tags.map(String) : [];
            } else {
                return [];
            }
        }

        // If no valid JSON block found, try splitting by common delimiters as a fallback
        const tags = response.split(/[,;\n]/).map(tag => tag.trim()).filter(tag => tag.length > 0);
        return tags.length > 0 ? tags : [];

    } catch (e) {
        // Catch and safely return empty array on any parsing errors
        console.error('Failed to parse tags response: ', e);
        return [];
    }
};

export const generateEmoji = async (
    token: string = '',
    model: string,
    prompt: string,
    chat_id?: string
) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/emoji/completions`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            model: model,
            prompt: prompt,
            ...(chat_id && { chat_id: chat_id })
        })
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        // Original code returned null on error
        console.error("Error generating emoji:", error);
        // throw error; // Or uncomment to throw
        return null;
    }

    const response = res?.choices[0]?.message?.content.replace(/["']/g, '') ?? null;

    if (response) {
        // Use a more robust regex to find the first emoji
        const emojiMatch = response.match(/\p{Extended_Pictographic}/u);
        if (emojiMatch) {
            return emojiMatch[0]; // Return the first matched emoji
        }
    }

    return null; // Return null if no emoji found or error occurred
};

export const generateQueries = async (
    token: string = '',
    model: string,
    messages: object[],
    prompt: string,
    type?: string = 'web_search'
) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/queries/completions`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            model: model,
            messages: messages,
            prompt: prompt,
            type: type
        })
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        // Original code returned [response] (which would be null here) or empty array on error
        console.error("Error generating queries:", error);
        // throw error; // Or uncomment to throw
        return [];
    }

    // Step 1: Safely extract the response string
    const response = res?.choices[0]?.message?.content ?? '';
    if (!response) return [];

    try {
        const jsonStartIndex = response.indexOf('{');
        const jsonEndIndex = response.lastIndexOf('}');

        if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
            const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);

            const parsed = JSON.parse(jsonResponse);

            if (parsed && parsed.queries) {
                // Ensure it's an array of strings
                return Array.isArray(parsed.queries) ? parsed.queries.map(String) : [];
            } else {
                return [];
            }
        }

        // If no valid JSON block found, return the whole response as a single-element array if not empty
        return response ? [response] : [];
    } catch (e) {
        // Catch parsing errors, return the raw response in an array as a fallback
        console.error('Failed to parse queries response: ', e);
        return response ? [response] : [];
    }
};

export const generateAutoCompletion = async (
    token: string = '',
    model: string,
    prompt: string,
    messages?: object[],
    type: string = 'search query'
) => {
    const controller = new AbortController(); // Controller not used for aborting here, but kept from original
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/auto/completions`, {
        signal: controller.signal, // Signal is present but not used to abort on error currently
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            model: model,
            prompt: prompt,
            ...(messages && { messages: messages }),
            type: type,
            stream: false // Explicitly false
        })
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        // Original code returned "" on error
        console.error("Error generating auto-completion:", error);
        // throw error; // Or uncomment to throw
        return "";
    }

    const response = res?.choices[0]?.message?.content ?? '';
    if (!response) return "";

    try {
        const jsonStartIndex = response.indexOf('{');
        const jsonEndIndex = response.lastIndexOf('}');

        if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
            const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);
            const parsed = JSON.parse(jsonResponse);

            if (parsed && typeof parsed.text === 'string') { // Check if text property exists and is string
                return parsed.text;
            } else {
                return ''; // Return empty if structure incorrect
            }
        }

        // If no valid JSON block found, return the whole response string
        return response;
    } catch (e) {
        // Catch parsing errors, return the raw response string as fallback
        console.error('Failed to parse auto-completion response: ', e);
        return response;
    }
};

export const generateMoACompletion = async (
    token: string = '',
    model: string,
    prompt: string,
    responses: string[]
) => {
    const controller = new AbortController();
    let error = null;
    let response: Response | null = null;

    try {
        response = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/moa/completions`, {
            signal: controller.signal,
            method: 'POST',
            headers: {
                Accept: 'application/json', // Assuming stream returns JSON chunks
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
                model: model,
                prompt: prompt,
                responses: responses,
                stream: true
            })
        });

        // Check 401 immediately
        if (response.status === 401 && token) {
            handleApiUnauthorized();
            throw new Error('Unauthorized'); // Abort processing
        }

        // Check other errors
        if (!response.ok) {
            let errorDetail = `HTTP error! status: ${response.status}`;
             try {
                 const errJson = await response.json();
                 errorDetail = errJson.detail ?? errorDetail;
             } catch (e) { /* Ignore JSON parsing errors for non-JSON error responses */ }
            throw new Error(errorDetail);
        }
    } catch (err) {
        console.log(err); // Original log
        error = err instanceof Error ? err : new Error(String(err));
        response = null; // Nullify response on error
        if (!controller.signal.aborted){
            controller.abort(); // Abort if fetch failed or status bad
        }
    }

    if (error && response === null) {
        throw error; // Throw if fetch failed or 401 occurred
    }

    return [response, controller]; // Return potentially null response and controller
};

export const getPipelinesList = async (token: string = '') => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/list`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        }
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    let pipelines = res?.data ?? [];
    return pipelines; // Returns pipelines array or [] on error
};

export const uploadPipeline = async (token: string, file: File, urlIdx: string) => {
    let error = null;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('urlIdx', urlIdx); // Make sure backend expects urlIdx in form data

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/upload`, {
        method: 'POST',
        headers: {
            ...(token && { authorization: `Bearer ${token}` })
            // Content-Type is set automatically by browser for FormData
        },
        body: formData
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const downloadPipeline = async (token: string, url: string, urlIdx: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/add`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        },
        body: JSON.stringify({
            url: url,
            urlIdx: urlIdx
        })
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const deletePipeline = async (token: string, id: string, urlIdx: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/delete`, {
        method: 'DELETE',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        },
        body: JSON.stringify({
            id: id, // Ensure backend expects 'id' not 'pipeline_id'
            urlIdx: urlIdx
        })
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getPipelines = async (token: string, urlIdx?: string) => {
    let error = null;

    const searchParams = new URLSearchParams();
    if (urlIdx !== undefined) {
        searchParams.append('urlIdx', urlIdx);
    }

    const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/?${searchParams.toString()}`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        }
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    let pipelines = res?.data ?? [];
    return pipelines; // Returns pipelines array or [] on error
};

export const getPipelineValves = async (token: string, pipeline_id: string, urlIdx: string) => {
    let error = null;

    const searchParams = new URLSearchParams();
    // urlIdx seems required based on function signature, always add it
    searchParams.append('urlIdx', urlIdx);

    const res = await fetch(
        `${WEBUI_BASE_URL}/api/v1/pipelines/${pipeline_id}/valves?${searchParams.toString()}`,
        {
            method: 'GET',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                ...(token && { authorization: `Bearer ${token}` })
            }
        }
    )
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getPipelineValvesSpec = async (token: string, pipeline_id: string, urlIdx: string) => {
    let error = null;

    const searchParams = new URLSearchParams();
    searchParams.append('urlIdx', urlIdx);

    const res = await fetch(
        `${WEBUI_BASE_URL}/api/v1/pipelines/${pipeline_id}/valves/spec?${searchParams.toString()}`,
        {
            method: 'GET',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                ...(token && { authorization: `Bearer ${token}` })
            }
        }
    )
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const updatePipelineValves = async (
    token: string = '', // Token might be optional based on usage, keep as optional
    pipeline_id: string,
    valves: object,
    urlIdx: string
) => {
    let error = null;

    const searchParams = new URLSearchParams();
    searchParams.append('urlIdx', urlIdx);

    const res = await fetch(
        `${WEBUI_BASE_URL}/api/v1/pipelines/${pipeline_id}/valves/update?${searchParams.toString()}`,
        {
            method: 'POST',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                ...(token && { authorization: `Bearer ${token}` })
            },
            body: JSON.stringify(valves)
        }
    )
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

// No Authorization header, no 401 check needed
export const getBackendConfig = async () => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/config`, {
        method: 'GET',
        credentials: 'include', // Include cookies if necessary for session checking elsewhere
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json(); // Still check if response is ok
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

// No Authorization header, no 401 check needed
export const getChangelog = async () => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/changelog`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json(); // Still check if response is ok
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getVersionUpdates = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/version/updates`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getModelFilterConfig = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/config/model/filter`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const updateModelFilterConfig = async (
    token: string,
    enabled: boolean,
    models: string[]
) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/config/model/filter`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            enabled: enabled,
            models: models
        })
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getWebhookUrl = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/webhook`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res?.url; // Return url property or undefined
};

export const updateWebhookUrl = async (token: string, url: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/webhook`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            url: url
        })
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res?.url; // Return url property or undefined
};

export const getCommunitySharingEnabledStatus = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/community_sharing`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res; // Return the whole response object or null
};

export const toggleCommunitySharingEnabledStatus = async (token: string) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/community_sharing/toggle`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            if ('detail' in err) {
                error = err.detail;
            } else {
                error = err instanceof Error ? err.message : err;
            }
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};

export const getModelConfig = async (token: string): Promise<GlobalModelConfig> => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/config/models`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        }
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        // Returning empty array to match Promise<GlobalModelConfig> which expects an array
        return [];
        // throw error; // Or uncomment to throw
    }

    return res?.models ?? []; // Return models array or empty array on error/null response
};

// Keep existing type definitions
export interface ModelConfig {
    id: string;
    name: string;
    meta: ModelMeta;
    base_model_id?: string;
    params: ModelParams;
}
export interface ModelMeta {
    description?: string;
    capabilities?: object;
    profile_image_url?: string;
}
export interface ModelParams {}
export type GlobalModelConfig = ModelConfig[];


export const updateModelConfig = async (token: string, config: GlobalModelConfig) => {
    let error = null;

    const res = await fetch(`${WEBUI_BASE_URL}/api/config/models`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            models: config
        })
    })
        .then(async (res) => {
            if (res.status === 401) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json();
        })
        .catch((err) => {
            console.log(err);
            error = err instanceof Error ? err.message : err.detail ?? err;
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};
