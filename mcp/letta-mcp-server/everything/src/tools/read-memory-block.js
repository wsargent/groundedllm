/**
 * Tool handler for reading a memory block in the Letta system
 */
export async function handleReadMemoryBlock(server, args) {
    try {
        // Validate arguments
        if (!args?.block_id) {
            throw new Error('Missing required argument: block_id');
        }
        
        // Headers for API requests
        const headers = server.getApiHeaders();
        
        // If agent_id is provided, set the user_id header
        if (args.agent_id) {
            headers['user_id'] = args.agent_id;
        }
        
        // Get the memory block
        const response = await server.api.get(`/blocks/${args.block_id}`, {
            headers,
        });
        
        // Format the response
        return {
            content: [{
                type: 'text',
                text: JSON.stringify({
                    success: true,
                    block: response.data
                }, null, 2),
            }]
        };
    } catch (error) {
        return server.createErrorResponse(error);
    }
}

/**
 * Tool definition for read_memory_block
 */
export const readMemoryBlockToolDefinition = {
    name: 'read_memory_block',
    description: 'Get full details of a specific memory block by ID',
    inputSchema: {
        type: 'object',
        properties: {
            block_id: {
                type: 'string',
                description: 'ID of the memory block to retrieve'
            },
            agent_id: {
                type: 'string',
                description: 'Optional agent ID for authorization'
            }
        },
        required: ['block_id']
    }
};