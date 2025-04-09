/**
 * Tool handler for updating a memory block in the Letta system
 */
export async function handleUpdateMemoryBlock(server, args) {
    try {
        // Validate arguments
        if (!args?.block_id) {
            throw new Error('Missing required argument: block_id');
        }
        
        if (!args?.value && !args?.metadata) {
            throw new Error('Either value or metadata must be provided');
        }
        
        // Headers for API requests
        const headers = server.getApiHeaders();
        
        // If agent_id is provided, set the user_id header
        if (args.agent_id) {
            headers['user_id'] = args.agent_id;
        }
        
        // Prepare update data
        const updateData = {};
        if (args.value !== undefined) {
            updateData.value = args.value;
        }
        if (args.metadata !== undefined) {
            updateData.metadata = args.metadata;
        }
        
        // Update the memory block
        const response = await server.api.patch(`/blocks/${args.block_id}`, updateData, { headers });
        
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
 * Tool definition for update_memory_block
 */
export const updateMemoryBlockToolDefinition = {
    name: 'update_memory_block',
    description: 'Update the contents and metadata of a memory block',
    inputSchema: {
        type: 'object',
        properties: {
            block_id: {
                type: 'string',
                description: 'ID of the memory block to update'
            },
            value: {
                type: 'string',
                description: 'New value for the memory block (optional)'
            },
            metadata: {
                type: 'object',
                description: 'New metadata for the memory block (optional)'
            },
            agent_id: {
                type: 'string',
                description: 'Optional agent ID for authorization'
            }
        },
        required: ['block_id']
    }
};