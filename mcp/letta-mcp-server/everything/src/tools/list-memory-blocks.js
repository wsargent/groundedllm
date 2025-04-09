/**
 * Tool handler for listing memory blocks in the Letta system
 */
export async function handleListMemoryBlocks(server, args) {
    try {
        // Headers for API requests
        const headers = server.getApiHeaders();
        
        // If agent_id is provided, set the user_id header
        if (args && args.agent_id) {
            headers['user_id'] = args.agent_id;
        }
        
        // Prepare query parameters for the blocks endpoint
        const queryParams = {};
        
        // Add label filter if provided
        if (args && args.label) {
            queryParams.label = args.label;
        }
        
        // Add templates_only filter (default to false if not provided)
        queryParams.templates_only = args && args.templates_only !== undefined ? args.templates_only : false;
        
        // Add name filter if provided
        if (args && args.name) {
            queryParams.name = args.name;
        }
        
        // Get blocks from the Letta server
        let endpoint = '/blocks';
        if (args && args.agent_id) {
            // If agent_id is provided, use the agent-specific blocks endpoint
            endpoint = `/agents/${args.agent_id}/core-memory/blocks`;
        }
        
        const blocksResponse = await server.api.get(endpoint, {
            headers,
            params: queryParams
        });
        
        let blocks = blocksResponse.data;
        
        // Apply text filter if provided (this is separate from the API's label/name filters)
        if (args && args.filter && typeof args.filter === 'string') {
            const filterLower = args.filter.toLowerCase();
            blocks = blocks.filter((block) => 
                (block.name && block.name.toLowerCase().includes(filterLower)) ||
                (block.label && block.label.toLowerCase().includes(filterLower)) ||
                (block.value && typeof block.value === 'string' && block.value.toLowerCase().includes(filterLower))
            );
        }
        
        // Apply pagination
        const page = args && typeof args.page === 'number' ? Math.max(1, args.page) : 1;
        const pageSize = args && typeof args.pageSize === 'number' ? Math.max(1, Math.min(100, args.pageSize)) : 10;
        const startIndex = (page - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        const totalBlocks = blocks.length;
        const totalPages = Math.ceil(totalBlocks / pageSize);
        const paginatedBlocks = blocks.slice(startIndex, endIndex);
        
        // Format blocks for output
        const formattedBlocks = paginatedBlocks.map((block) => {
            const result = {
                id: block.id,
                name: block.name || 'Unnamed Block',
                label: block.label || 'No Label',
                metadata: block.metadata || {},
                limit: block.limit || 5000,
                created_at: block.created_at,
                updated_at: block.updated_at
            };
            
            // Include full content or truncated preview based on args
            if (args && args.include_full_content) {
                result.value = block.value;
            } else {
                // Truncate value if it's too long
                let value = block.value;
                if (typeof value === 'string') {
                    result.value_preview = value.length > 200 ? value.substring(0, 200) + '...' : value;
                } else {
                    result.value_preview = 'Non-string value';
                }
            }
            
            // Add agents using this block if available
            if (block.agents && Array.isArray(block.agents)) {
                result.agents = block.agents.map((agent) => ({
                    id: agent.id,
                    name: agent.name
                }));
            }
            
            return result;
        });
        
        // Format the response
        return {
            content: [{
                type: 'text',
                text: JSON.stringify({
                    success: true,
                    pagination: {
                        page: page,
                        pageSize: pageSize,
                        totalBlocks: totalBlocks,
                        totalPages: totalPages,
                        hasNextPage: page < totalPages,
                        hasPreviousPage: page > 1
                    },
                    block_count: formattedBlocks.length,
                    blocks: formattedBlocks,
                    agent_specific: args && args.agent_id ? true : false,
                    filters: {
                        label: args?.label,
                        name: args?.name,
                        templates_only: args?.templates_only,
                        text_filter: args?.filter
                    }
                }, null, 2),
            }],
        };
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for list_memory_blocks
 */
export const listMemoryBlocksToolDefinition = {
    name: 'list_memory_blocks',
    description: 'List all memory blocks available in the Letta system',
    inputSchema: {
        type: 'object',
        properties: {
            filter: {
                type: 'string',
                description: 'Optional filter to search for specific blocks by name or content',
            },
            agent_id: {
                type: 'string',
                description: 'Optional agent ID to list blocks for a specific agent',
            },
            page: {
                type: 'number',
                description: 'Page number for pagination (starts at 1)',
            },
            pageSize: {
                type: 'number',
                description: 'Number of blocks per page (1-100, default: 10)',
            },
            label: {
                type: 'string',
                description: 'Optional filter for block label (e.g., "human", "persona")',
            },
            templates_only: {
                type: 'boolean',
                description: 'Whether to include only templates (default: false)',
            },
            name: {
                type: 'string',
                description: 'Optional filter for block name',
            },
            include_full_content: {
                type: 'boolean',
                description: 'Whether to include the full content of blocks (default: false)',
            },
        },
        required: [],
    },
};