# Web Loaders in Open WebUI

This document explains the different web loaders available in Open WebUI and when to use each one.

## Overview

Open WebUI uses web loaders to fetch and process content from web pages. Currently, there are multiple loader implementations available.

## Available Loaders

### loader.js
Location: `backend/open_webui/static/loader.js`

**Purpose:** Frontend loading indicator and UI feedback for web operations.

**Use case:** Provides visual feedback to users when web content is being fetched or processed.

### static/loader.js
Location: `static/static/loader.js`

**Purpose:** Static asset loader for deployment builds.

**Use case:** Used in production builds to handle static resource loading.

## Performance Considerations

When implementing web loading functionality:
- Use appropriate loader based on context (frontend vs backend)
- Consider caching strategies for frequently accessed web content
- Implement timeout mechanisms for slow-loading pages

## Related Documentation

- For web search configuration, see [Web Search Documentation]
- For API endpoint documentation, see [API Documentation]

## Contributing

If you've identified additional loaders or improvements to this documentation, please submit a pull request.
